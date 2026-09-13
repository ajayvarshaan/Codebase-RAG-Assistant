from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database.database import SessionLocal
from models.project import Project

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
    db: Session = Depends(get_db)
):
    project = (
        db.query(Project)
        .filter(
            Project.id == project_id
        )
        .first()
    )

    if not project:
        raise HTTPException(
            status_code=404,
            detail="Project not found"
        )

    readme = generate_readme(
        db=db,
        project_id=project_id
    )

    return {
        "project_id": project_id,
        "project_name": project.name,
        "readme": readme
    }
