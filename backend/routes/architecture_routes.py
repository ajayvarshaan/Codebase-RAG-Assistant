from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database.database import SessionLocal
from models.project import Project

from services.architecture_service import generate_architecture_summary


router = APIRouter(
    prefix="/architecture",
    tags=["Architecture"]
)


def get_db():
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()


@router.get("/project/{project_id}")
def get_architecture_summary(
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

    summary = generate_architecture_summary(
        db=db,
        project_id=project_id
    )

    return {
        "project_id": project_id,
        "project_name": project.name,
        "summary": summary
    }
