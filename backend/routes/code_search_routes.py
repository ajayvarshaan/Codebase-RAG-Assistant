from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database.database import SessionLocal
from models.project import Project

from services.code_search_service import search_codebase


router = APIRouter(
    prefix="/code-search",
    tags=["Code Search"]
)


def get_db():
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()


@router.get("/project/{project_id}")
def search_project_code(
    project_id: int,
    query: str,
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

    results = search_codebase(
        db=db,
        project_id=project_id,
        query=query
    )

    return {
        "project_id": project_id,
        "query": query,
        "results": results
    }