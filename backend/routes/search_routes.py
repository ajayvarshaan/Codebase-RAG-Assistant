from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database.database import SessionLocal
from services.retrieval import search_similar_chunks

router = APIRouter(prefix="/search", tags=["Search"])


class SearchRequest(BaseModel):
    query: str
    top_k: int = 5


def get_db():
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()


@router.post("/project/{project_id}")
def search_project(
    project_id: int,
    request: SearchRequest,
    db: Session = Depends(get_db)
):
    chunks = search_similar_chunks(
        db=db,
        query=request.query,
        project_id=project_id,
        top_k=request.top_k
    )

    return [
        {
            "id": chunk.id,
            "file_id": chunk.file_id,
            "chunk_index": chunk.chunk_index,
            "content": chunk.content,
            "start_line": chunk.start_line,
            "end_line": chunk.end_line
        }
        for chunk in chunks
    ]