from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database.database import SessionLocal
from models.code_chunk import CodeChunk
from models.code_file import CodeFile
from models.project import Project
from services.chunking import split_code_into_chunks
from services.embedding_service import (
    EMBEDDING_MODEL,
    create_embedding,
)

router = APIRouter(prefix="/chunks", tags=["Chunks"])


def get_db():
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()


@router.post("/project/{project_id}")
def create_chunks_for_project(
    project_id: int,
    db: Session = Depends(get_db)
):
    project = (
        db.query(Project)
        .filter(Project.id == project_id)
        .first()
    )

    if not project:
        raise HTTPException(
            status_code=404,
            detail="Project not found"
        )

    files = (
        db.query(CodeFile)
        .filter(CodeFile.project_id == project_id)
        .all()
    )

    if not files:
        raise HTTPException(
            status_code=404,
            detail="No code files found for this project"
        )

    chunks_to_save = []

    try:
        for file in files:
            chunks = split_code_into_chunks(file.content)

            for chunk in chunks:
                embedding = create_embedding(
                    chunk["content"]
                )

                code_chunk = CodeChunk(
                    project_id=project_id,
                    file_id=file.id,
                    content=chunk["content"],
                    chunk_index=chunk["chunk_index"],
                    start_line=chunk["start_line"],
                    end_line=chunk["end_line"],
                    embedding=embedding,
                    embedding_model=EMBEDDING_MODEL
                )

                chunks_to_save.append(code_chunk)

    except Exception as error:
        db.rollback()

        raise HTTPException(
            status_code=500,
            detail=f"Could not generate embeddings: {str(error)}"
        )

    db.query(CodeChunk).filter(
        CodeChunk.project_id == project_id
    ).delete(synchronize_session=False)

    db.add_all(chunks_to_save)
    db.commit()

    return {
        "message": "Code chunks and embeddings created successfully",
        "project_id": project_id,
        "files_processed": len(files),
        "chunks_created": len(chunks_to_save),
        "embedding_model": EMBEDDING_MODEL
    }