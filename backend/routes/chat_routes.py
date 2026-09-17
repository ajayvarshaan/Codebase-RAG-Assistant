from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database.database import SessionLocal
from models.code_file import CodeFile
from models.code_chunk import CodeChunk
from models.code_relationship import CodeRelationship
from models.project import Project
from models.user import User
from services.auth_dependency import get_current_user

from services.retrieval import search_similar_chunks
from services.generation_service import generate_answer


router = APIRouter(prefix="/chat", tags=["Chat"])


# ============================================================
# CONFIGURATION
# ============================================================

# Maximum number of complete files to add to the AI context.
MAX_FULL_FILES = 2

# Prevent very large files from consuming the entire
# LLM context.
MAX_FULL_FILE_CHARS = 20000


# ============================================================
# REQUEST MODELS
# ============================================================

class ConversationMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    question: str
    top_k: int = 5
    conversation_history: list[ConversationMessage] = []


# ============================================================
# DATABASE
# ============================================================

def get_db():
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()


# ============================================================
# FIND EXPLICITLY MENTIONED FILES
# ============================================================

def find_mentioned_files(
    db: Session,
    project_id: int,
    question: str
):
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

        # ----------------------------------------------------
        # Full file path mentioned
        # ----------------------------------------------------

        if file_path_lower in question_lower:

            mentioned_files.append(
                code_file
            )

            continue

        # ----------------------------------------------------
        # File name mentioned
        # ----------------------------------------------------

        if file_name_lower in question_lower:

            mentioned_files.append(
                code_file
            )

            continue

        # ----------------------------------------------------
        # File name without extension
        # ----------------------------------------------------

        if "." in file_name:

            file_name_without_extension = (
                file_name.rsplit(".", 1)[0]
            ).lower()

            if (
                len(file_name_without_extension) > 2
                and file_name_without_extension
                in question_lower
            ):

                mentioned_files.append(
                    code_file
                )

    return mentioned_files


# ============================================================
# FULL-FILE REQUEST DETECTION
# ============================================================

def is_full_file_request(
    question: str
) -> bool:
    """
    Detect whether the user wants actual file/code content.

    Examples:

    Show me the main Python code.
    Show hello.py.
    Show the full code.
    Explain hello.py.
    Explain this file.
    """

    question_lower = question.lower().strip()

    full_file_phrases = [
        "show me the code",
        "show me code",
        "show the code",
        "show code",
        "show me the full code",
        "show the full code",
        "show full code",
        "show me the complete code",
        "show the complete code",
        "show complete code",
        "show me the source code",
        "show the source code",
        "show source code",
        "give me the code",
        "give me the full code",
        "give me the complete code",
        "give me the source code",
        "provide the code",
        "provide the full code",
        "provide the complete code",
        "display the code",
        "display the full code",
        "explain this file",
        "explain the file",
        "explain this code",
        "explain the code",
        "explain the source",
        "walk me through this file",
        "walk through this file",
        "main python code",
        "main javascript code",
        "main typescript code",
        "main java code",
    ]

    if any(
        phrase in question_lower
        for phrase in full_file_phrases
    ):
        return True

    # --------------------------------------------------------
    # Detect action + file/source reference
    # --------------------------------------------------------

    action_words = [
        "show",
        "display",
        "give",
        "provide",
        "explain",
    ]

    file_words = [
        ".py",
        ".js",
        ".jsx",
        ".ts",
        ".tsx",
        ".java",
        ".c",
        ".cpp",
        ".cs",
        ".go",
        ".rs",
        ".php",
        ".rb",
        ".swift",
        ".kt",
        ".dart",
        "file",
        "script",
        "source",
    ]

    has_action = any(
        word in question_lower
        for word in action_words
    )

    has_file_reference = any(
        word in question_lower
        for word in file_words
    )

    return (
        has_action
        and has_file_reference
    )


# ============================================================
# FIND SOURCE FILES FOR CODE REQUESTS
# ============================================================

def find_source_files_for_request(
    db: Session,
    project_id: int,
    question: str
):
    """
    Find source files directly when the user asks
    for code but does not explicitly mention a filename.

    Example:

        "Show me the main Python code."

    This should find:

        hello.py
    """

    question_lower = question.lower()

    # --------------------------------------------------------
    # Language -> extensions
    # --------------------------------------------------------

    extension_map = {
        "python": [".py"],
        "javascript": [".js", ".jsx"],
        "typescript": [".ts", ".tsx"],
        "java": [".java"],
        "c++": [".cpp"],
        "cpp": [".cpp"],
        "c": [".c"],
        "c#": [".cs"],
        "csharp": [".cs"],
        "go": [".go"],
        "rust": [".rs"],
        "php": [".php"],
        "ruby": [".rb"],
        "swift": [".swift"],
        "kotlin": [".kt"],
        "dart": [".dart"],
    }

    requested_extensions = []

    for language, extensions in extension_map.items():

        if language in question_lower:

            requested_extensions.extend(
                extensions
            )

    # --------------------------------------------------------
    # Supported source extensions
    # --------------------------------------------------------

    source_extensions = [
        ".py",
        ".js",
        ".jsx",
        ".ts",
        ".tsx",
        ".java",
        ".c",
        ".cpp",
        ".cs",
        ".go",
        ".rs",
        ".php",
        ".rb",
        ".swift",
        ".kt",
        ".dart",
    ]

    # If no specific language was mentioned,
    # search all supported source files.
    if not requested_extensions:

        requested_extensions = (
            source_extensions
        )

    # --------------------------------------------------------
    # Load project files
    # --------------------------------------------------------

    project_files = (
        db.query(CodeFile)
        .filter(
            CodeFile.project_id == project_id
        )
        .all()
    )

    matching_files = []

    for code_file in project_files:

        path_lower = (
            code_file.file_path.lower()
        )

        if any(
            path_lower.endswith(extension)
            for extension in requested_extensions
        ):

            matching_files.append(
                code_file
            )

    # --------------------------------------------------------
    # Prefer likely main files
    # --------------------------------------------------------

    def source_priority(code_file):

        file_name = (
            code_file.file_path
            .split("/")[-1]
            .lower()
        )

        priority = 0

        main_file_names = [
            "main.py",
            "app.py",
            "index.py",
            "server.py",
            "hello.py",
            "main.js",
            "app.js",
            "index.js",
            "main.ts",
            "app.ts",
            "index.ts",
        ]

        if file_name in main_file_names:

            priority += 10

        return priority

    matching_files.sort(
        key=source_priority,
        reverse=True
    )

    return matching_files


# ============================================================
# CHAT ENDPOINT
# ============================================================

@router.post("/project/{project_id}")
def chat_with_codebase(
    project_id: int,
    chat_data: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    # ========================================================
    # Verify project ownership
    # ========================================================

    project = (
        db.query(Project)
        .filter(
            Project.id == project_id,
            Project.user_id == current_user.id
        )
        .first()
    )

    if not project:

        raise HTTPException(
            status_code=404,
            detail="Project not found"
        )

    # ========================================================
    # Build retrieval query
    # ========================================================

    retrieval_query = chat_data.question

    if chat_data.conversation_history:

        previous_messages = []

        for message in (
            chat_data.conversation_history[-4:]
        ):

            previous_messages.append(
                f"{message.role}: {message.content}"
            )

        retrieval_query = (
            "Use the previous conversation to "
            "understand the current question.\n\n"
            "Previous conversation:\n"
            + "\n".join(previous_messages)
            + "\n\nCurrent question:\n"
            + chat_data.question
        )

    # ========================================================
    # Hybrid + code-aware retrieval
    # ========================================================

    chunks = search_similar_chunks(
        db=db,
        query=retrieval_query,
        project_id=project_id,
        top_k=chat_data.top_k
    )

    # ========================================================
    # Explicitly mentioned files
    # ========================================================

    mentioned_files = find_mentioned_files(
        db=db,
        project_id=project_id,
        question=chat_data.question
    )

    # ========================================================
    # Detect full-file request
    # ========================================================

    full_file_request = is_full_file_request(
        chat_data.question
    )

    # ========================================================
    # Find source files for generic code requests
    #
    # Example:
    #
    # "Show me the main Python code."
    #
    # This can find hello.py even if vector retrieval
    # didn't return hello.py.
    # ========================================================

    source_files = []

    if full_file_request:

        source_files = find_source_files_for_request(
            db=db,
            project_id=project_id,
            question=chat_data.question
        )

    # ========================================================
    # Existing chunk IDs
    # ========================================================

    existing_chunk_ids = {
        chunk.id
        for chunk in chunks
    }

    # ========================================================
    # File IDs
    # ========================================================

    mentioned_file_ids = {
        code_file.id
        for code_file in mentioned_files
    }

    source_file_ids = {
        code_file.id
        for code_file in source_files
    }

    all_requested_file_ids = (
        mentioned_file_ids
        | source_file_ids
    )

    # ========================================================
    # Load chunks for explicitly mentioned/source files
    # ========================================================

    if all_requested_file_ids:

        direct_chunks = (
            db.query(CodeChunk)
            .filter(
                CodeChunk.project_id == project_id,
                CodeChunk.file_id.in_(
                    all_requested_file_ids
                )
            )
            .order_by(
                CodeChunk.file_id,
                CodeChunk.chunk_index
            )
            .all()
        )

        for chunk in direct_chunks:

            if chunk.id not in existing_chunk_ids:

                chunks.append(
                    chunk
                )

                existing_chunk_ids.add(
                    chunk.id
                )

    # ========================================================
    # Load all files needed by current context
    # ========================================================

    file_ids = {
        chunk.file_id
        for chunk in chunks
    }

    # Include explicitly mentioned files.
    file_ids.update(
        all_requested_file_ids
    )

    if file_ids:

        code_files = (
            db.query(CodeFile)
            .filter(
                CodeFile.project_id == project_id,
                CodeFile.id.in_(file_ids)
            )
            .all()
        )

    else:

        code_files = []

    file_cache = {
        code_file.id: code_file
        for code_file in code_files
    }

    # ========================================================
    # Load relationships
    # ========================================================

    relationships_by_file = {}

    if file_ids:

        relationships = (
            db.query(CodeRelationship)
            .filter(
                CodeRelationship.project_id == project_id,
                (
                    (
                        CodeRelationship.source_file_id.in_(
                            file_ids
                        )
                    )
                    |
                    (
                        CodeRelationship.target_file_id.in_(
                            file_ids
                        )
                    )
                )
            )
            .all()
        )

        related_file_ids = set()

        for relationship in relationships:

            source_id = (
                relationship.source_file_id
            )

            target_id = (
                relationship.target_file_id
            )

            # ------------------------------------------------
            # Outgoing relationship
            # ------------------------------------------------

            if source_id in file_ids:

                relationships_by_file.setdefault(
                    source_id,
                    []
                ).append(
                    {
                        "file_id": target_id,
                        "relationship": (
                            relationship.relationship_type
                        ),
                        "direction": "outgoing"
                    }
                )

                related_file_ids.add(
                    target_id
                )

            # ------------------------------------------------
            # Incoming relationship
            # ------------------------------------------------

            if target_id in file_ids:

                relationships_by_file.setdefault(
                    target_id,
                    []
                ).append(
                    {
                        "file_id": source_id,
                        "relationship": (
                            relationship.relationship_type
                        ),
                        "direction": "incoming"
                    }
                )

                related_file_ids.add(
                    source_id
                )

    else:

        related_file_ids = set()

    # ========================================================
    # Load related file metadata
    # ========================================================

    missing_file_ids = (
        related_file_ids
        - set(file_cache.keys())
    )

    if missing_file_ids:

        related_files = (
            db.query(CodeFile)
            .filter(
                CodeFile.project_id == project_id,
                CodeFile.id.in_(
                    missing_file_ids
                )
            )
            .all()
        )

        for code_file in related_files:

            file_cache[code_file.id] = (
                code_file
            )

    # ========================================================
    # Determine complete files to load
    # ========================================================

    full_file_ids = []

    # --------------------------------------------------------
    # Priority 1:
    # Explicitly mentioned files
    # --------------------------------------------------------

    for code_file in mentioned_files:

        if code_file.id not in full_file_ids:

            full_file_ids.append(
                code_file.id
            )

        if len(full_file_ids) >= MAX_FULL_FILES:

            break

    # --------------------------------------------------------
    # Priority 2:
    # Source files identified from the question
    #
    # Example:
    #
    # "Show me the main Python code."
    #
    # -> hello.py
    # --------------------------------------------------------

    if len(full_file_ids) < MAX_FULL_FILES:

        for code_file in source_files:

            if code_file.id in full_file_ids:

                continue

            full_file_ids.append(
                code_file.id
            )

            if len(full_file_ids) >= MAX_FULL_FILES:

                break

    # --------------------------------------------------------
    # Priority 3:
    # Source files returned by retrieval
    # --------------------------------------------------------

    if (
        full_file_request
        and len(full_file_ids)
        < MAX_FULL_FILES
    ):

        source_extensions = (
            ".py",
            ".js",
            ".jsx",
            ".ts",
            ".tsx",
            ".java",
            ".c",
            ".cpp",
            ".cs",
            ".go",
            ".rs",
            ".php",
            ".rb",
            ".swift",
            ".kt",
            ".dart",
        )

        for chunk in chunks:

            code_file = file_cache.get(
                chunk.file_id
            )

            if not code_file:

                continue

            file_path_lower = (
                code_file.file_path.lower()
            )

            if not file_path_lower.endswith(
                source_extensions
            ):

                continue

            if code_file.id in full_file_ids:

                continue

            full_file_ids.append(
                code_file.id
            )

            if len(full_file_ids) >= MAX_FULL_FILES:

                break

    # ========================================================
    # Build context
    # ========================================================

    context_parts = []

    added_relationships = set()

    all_related_file_ids = set()

    # ========================================================
    # Add complete file contents
    # ========================================================

    added_full_file_ids = set()

    if full_file_request:

        for file_id in full_file_ids:

            code_file = file_cache.get(
                file_id
            )

            if not code_file:

                continue

            content = (
                code_file.content
                or ""
            )

            # ------------------------------------------------
            # Prevent very large files from consuming
            # the entire model context.
            # ------------------------------------------------

            is_truncated = (
                len(content)
                > MAX_FULL_FILE_CHARS
            )

            if is_truncated:

                content_for_ai = (
                    content[
                        :MAX_FULL_FILE_CHARS
                    ]
                )

            else:

                content_for_ai = content

            context_parts.append(
                f"""
Complete file:
File: {code_file.file_path}

Full file content:

{content_for_ai}
"""
            )

            if is_truncated:

                context_parts.append(
                    f"""
Note:
The file {code_file.file_path} is larger than the
maximum context limit, so only the first
{MAX_FULL_FILE_CHARS} characters were included.
"""
                )

            added_full_file_ids.add(
                code_file.id
            )

    # ========================================================
    # Add retrieved chunks
    # ========================================================

    for chunk in chunks:

        code_file = file_cache.get(
            chunk.file_id
        )

        file_path = (
            code_file.file_path
            if code_file
            else "Unknown file"
        )

        # ----------------------------------------------------
        # Don't duplicate chunks when the complete file
        # was already added.
        # ----------------------------------------------------

        if chunk.file_id in added_full_file_ids:

            continue

        context_parts.append(
            f"""
File: {file_path}
Lines: {chunk.start_line}-{chunk.end_line}

{chunk.content}
"""
        )

        # ----------------------------------------------------
        # Add relationships
        # ----------------------------------------------------

        for related_file in (
            relationships_by_file.get(
                chunk.file_id,
                []
            )
        ):

            related_code_file = (
                file_cache.get(
                    related_file["file_id"]
                )
            )

            if not related_code_file:

                continue

            relationship_key = (
                chunk.file_id,
                related_file["file_id"],
                related_file["relationship"],
                related_file["direction"]
            )

            if relationship_key in added_relationships:

                continue

            added_relationships.add(
                relationship_key
            )

            all_related_file_ids.add(
                related_file["file_id"]
            )

            if (
                related_file["direction"]
                == "outgoing"
            ):

                relationship_text = (
                    f"{file_path} imports "
                    f"{related_code_file.file_path}"
                )

            else:

                relationship_text = (
                    f"{related_code_file.file_path} "
                    f"imports {file_path}"
                )

            context_parts.append(
                f"""
Code relationship:
{relationship_text}

Relationship type:
{related_file["relationship"]}
"""
            )

    # ========================================================
    # Load related chunks
    # ========================================================

    related_chunks = []

    if all_related_file_ids:

        related_chunks = (
            db.query(CodeChunk)
            .filter(
                CodeChunk.project_id == project_id,
                CodeChunk.file_id.in_(
                    all_related_file_ids
                )
            )
            .order_by(
                CodeChunk.file_id,
                CodeChunk.chunk_index
            )
            .all()
        )

    new_related_chunks = []

    for chunk in related_chunks:

        if chunk.id in existing_chunk_ids:

            continue

        existing_chunk_ids.add(
            chunk.id
        )

        new_related_chunks.append(
            chunk
        )

    chunks.extend(
        new_related_chunks
    )

    # ========================================================
    # Add related chunks to context
    # ========================================================

    for chunk in new_related_chunks:

        code_file = file_cache.get(
            chunk.file_id
        )

        file_path = (
            code_file.file_path
            if code_file
            else "Unknown file"
        )

        # Don't duplicate complete files.
        if chunk.file_id in added_full_file_ids:

            continue

        context_parts.append(
            f"""
Related file:
File: {file_path}
Lines: {chunk.start_line}-{chunk.end_line}

{chunk.content}
"""
        )

    # ========================================================
    # Final context
    # ========================================================

    context = "\n".join(
        context_parts
    )

    # ========================================================
    # Conversation history
    # ========================================================

    conversation_text = ""

    for message in (
        chat_data.conversation_history
    ):

        conversation_text += (
            f"{message.role.upper()}: "
            f"{message.content}\n\n"
        )

    # ========================================================
    # Generate AI answer
    # ========================================================

    answer = generate_answer(
        question=chat_data.question,
        context=context,
        conversation_history=conversation_text
    )

    # ========================================================
    # Build sources
    # ========================================================

    sources = []

    added_source_ids = set()

    for chunk in chunks:

        if chunk.id in added_source_ids:

            continue

        added_source_ids.add(
            chunk.id
        )

        code_file = file_cache.get(
            chunk.file_id
        )

        file_path = (
            code_file.file_path
            if code_file
            else "Unknown file"
        )

        sources.append(
            {
                "chunk_id": chunk.id,
                "file_id": chunk.file_id,
                "file_path": file_path,
                "start_line": chunk.start_line,
                "end_line": chunk.end_line
            }
        )

    # ========================================================
    # Return response
    # ========================================================

    return {
        "answer": answer,
        "sources": sources
    }