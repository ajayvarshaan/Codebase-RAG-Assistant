from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database.database import SessionLocal
from models.project import Project
from models.user import User

from services.auth_dependency import get_current_user
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
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    # ---------------------------------------------------------
    # Check project ownership
    # ---------------------------------------------------------

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


    # ---------------------------------------------------------
    # Search project code
    # ---------------------------------------------------------

    results = search_codebase(
        db=db,
        project_id=project_id,
        query=query
    )


    # ---------------------------------------------------------
    # Return result
    # ---------------------------------------------------------

    return {
        "project_id": project_id,
        "query": query,
        "results": results
    }