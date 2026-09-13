from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database.database import SessionLocal
from models.project import Project

router = APIRouter(prefix="/projects", tags=["Projects"])


def get_db():
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()


@router.post("/")
def create_project(
    name: str,
    description: str | None = None,
    db: Session = Depends(get_db)
):
    project = Project(
        name=name,
        description=description
    )

    db.add(project)
    db.commit()
    db.refresh(project)

    return {
        "id": project.id,
        "name": project.name,
        "description": project.description,
        "created_at": project.created_at
    }


@router.get("/")
def get_projects(db: Session = Depends(get_db)):
    projects = db.query(Project).all()

    return projects