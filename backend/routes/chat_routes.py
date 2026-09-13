from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database.database import SessionLocal
from models.code_file import CodeFile
from models.code_chunk import CodeChunk

from services.retrieval import search_similar_chunks
from services.generation_service import generate_answer
from services.relationship_service import get_related_files


router = APIRouter(prefix="/chat", tags=["Chat"])


# ---------------------------------------------------------
# Conversation message
# ---------------------------------------------------------

class ConversationMessage(BaseModel):
    role: str
    content: str


# ---------------------------------------------------------
# Chat request
# ---------------------------------------------------------

class ChatRequest(BaseModel):
    question: str
    top_k: int = 5
    conversation_history: list[ConversationMessage] = []


# ---------------------------------------------------------
# Database
# ---------------------------------------------------------

def get_db():
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()


# ---------------------------------------------------------
# Find files explicitly mentioned in the question
# ---------------------------------------------------------

def find_mentioned_files(
    db: Session,
    project_id: int,
    question: str
):
    """
    Find project files whose filename or path
    is explicitly mentioned in the question.
    """

    project_files = (
        db.query(CodeFile)
        .filter(
            CodeFile.project_id == project_id
        )
        .all()
    )

    question_lower = question.lower()

    mentioned_files = []

    for code_file in project_files:

        file_path = code_file.file_path
        file_name = file_path.split("/")[-1]

        file_path_lower = file_path.lower()
        file_name_lower = file_name.lower()

        # Match complete file path
        if file_path_lower in question_lower:
            mentioned_files.append(code_file)
            continue

        # Match filename
        if file_name_lower in question_lower:
            mentioned_files.append(code_file)
            continue

        # Match filename without extension
        if "." in file_name:

            file_name_without_extension = (
                file_name.rsplit(".", 1)[0]
            ).lower()

            if (
                len(file_name_without_extension) > 2
                and file_name_without_extension
                in question_lower
            ):
                mentioned_files.append(code_file)

    return mentioned_files


# ---------------------------------------------------------
# Chat with codebase
# ---------------------------------------------------------

@router.post("/project/{project_id}")
def chat_with_codebase(
    project_id: int,
    chat_data: ChatRequest,
    db: Session = Depends(get_db)
):

    # =====================================================
    # 1. Build better retrieval query using conversation
    # =====================================================

    retrieval_query = chat_data.question

    if chat_data.conversation_history:

        previous_messages = []

        for message in chat_data.conversation_history[-4:]:

            previous_messages.append(
                f"{message.role}: {message.content}"
            )

        retrieval_query = (
            "Use the previous conversation to understand "
            "the current question.\n\n"
            "Previous conversation:\n"
            + "\n".join(previous_messages)
            + "\n\nCurrent question:\n"
            + chat_data.question
        )

    # =====================================================
    # 2. Semantic RAG retrieval
    # =====================================================

    chunks = search_similar_chunks(
        db=db,
        query=retrieval_query,
        project_id=project_id,
        top_k=chat_data.top_k
    )

    # =====================================================
    # 3. Find files explicitly mentioned by the user
    # =====================================================

    mentioned_files = find_mentioned_files(
        db=db,
        project_id=project_id,
        question=chat_data.question
    )

    # =====================================================
    # 4. Add chunks from explicitly mentioned files
    # =====================================================

    existing_chunk_ids = {
        chunk.id
        for chunk in chunks
    }

    for code_file in mentioned_files:

        direct_chunks = (
            db.query(CodeChunk)
            .filter(
                CodeChunk.file_id == code_file.id,
                CodeChunk.project_id == project_id
            )
            .order_by(
                CodeChunk.chunk_index
            )
            .all()
        )

        for chunk in direct_chunks:

            if chunk.id not in existing_chunk_ids:

                chunks.append(chunk)

                existing_chunk_ids.add(
                    chunk.id
                )

    # =====================================================
    # 5. Build code context
    # =====================================================

    context_parts = []

    # Keep track of relationships already added
    added_relationships = set()

    # Keep track of related file IDs
    related_file_ids = set()

    for chunk in chunks:

        # -------------------------------------------------
        # Find file belonging to chunk
        # -------------------------------------------------

        code_file = (
            db.query(CodeFile)
            .filter(
                CodeFile.id == chunk.file_id
            )
            .first()
        )

        file_path = (
            code_file.file_path
            if code_file
            else "Unknown file"
        )

        # -------------------------------------------------
        # Add normal code context
        # -------------------------------------------------

        context_parts.append(
            f"""
File: {file_path}
Lines: {chunk.start_line}-{chunk.end_line}

{chunk.content}
"""
        )

        # =================================================
        # 6. Find related files
        # =================================================

        related_files = get_related_files(
            db=db,
            file_id=chunk.file_id,
            project_id=project_id
        )

        # -------------------------------------------------
        # Add relationship information
        # -------------------------------------------------

        for related_file in related_files:

            relationship_key = (
                chunk.file_id,
                related_file["file_id"],
                related_file["relationship"]
            )

            if relationship_key in added_relationships:
                continue

            added_relationships.add(
                relationship_key
            )

            related_file_ids.add(
                related_file["file_id"]
            )

            context_parts.append(
                f"""
Code relationship:
Source file: {file_path}
Relationship: {related_file["relationship"]}
Related file: {related_file["file_path"]}
"""
            )

    # =====================================================
    # 7. Add related file code to context
    # =====================================================

    related_chunks = []

    for related_file_id in related_file_ids:

        file_chunks = (
            db.query(CodeChunk)
            .filter(
                CodeChunk.file_id == related_file_id,
                CodeChunk.project_id == project_id
            )
            .order_by(
                CodeChunk.chunk_index
            )
            .all()
        )

        for chunk in file_chunks:

            if chunk.id in existing_chunk_ids:
                continue

            related_chunks.append(
                chunk
            )

            existing_chunk_ids.add(
                chunk.id
            )

    # Add related chunks to main chunks
    chunks.extend(
        related_chunks
    )

    # =====================================================
    # 8. Add related file code to AI context
    # =====================================================

    for chunk in related_chunks:

        code_file = (
            db.query(CodeFile)
            .filter(
                CodeFile.id == chunk.file_id
            )
            .first()
        )

        file_path = (
            code_file.file_path
            if code_file
            else "Unknown file"
        )

        context_parts.append(
            f"""
Related file:
File: {file_path}
Lines: {chunk.start_line}-{chunk.end_line}

{chunk.content}
"""
        )

    # =====================================================
    # 9. Combine context
    # =====================================================

    context = "\n".join(
        context_parts
    )

    # =====================================================
    # 10. Build conversation history
    # =====================================================

    conversation_text = ""

    for message in chat_data.conversation_history:

        conversation_text += (
            f"{message.role.upper()}: "
            f"{message.content}\n\n"
        )

    # =====================================================
    # 11. Generate AI answer
    # =====================================================

    answer = generate_answer(
        question=chat_data.question,
        context=context,
        conversation_history=conversation_text
    )

    # =====================================================
    # 12. Build sources
    # =====================================================

    sources = []

    added_source_ids = set()

    for chunk in chunks:

        if chunk.id in added_source_ids:
            continue

        added_source_ids.add(
            chunk.id
        )

        code_file = (
            db.query(CodeFile)
            .filter(
                CodeFile.id == chunk.file_id
            )
            .first()
        )

        file_path = (
            code_file.file_path
            if code_file
            else "Unknown file"
        )

        sources.append({
            "chunk_id": chunk.id,
            "file_id": chunk.file_id,
            "file_path": file_path,
            "start_line": chunk.start_line,
            "end_line": chunk.end_line
        })

    # =====================================================
    # 13. Return response
    # =====================================================

    return {
        "answer": answer,
        "sources": sources
    }