from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database.database import SessionLocal
from models.project import Project
from models.user import User

from services.auth_dependency import get_current_user
from services.readme_service import generate_readme


router = APIRouter(
    prefix="/readme",
    tags=["README Generator"]
)


def get_db():
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()


@router.get("/project/{project_id}")
def generate_project_readme(
    project_id: int,
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
    # Generate README
    # ---------------------------------------------------------

    readme = generate_readme(
        db=db,
        project_id=project_id
    )


    # ---------------------------------------------------------
    # Return result
    # ---------------------------------------------------------

    return {
        "project_id": project_id,
        "project_name": project.name,
        "readme": readme
    }