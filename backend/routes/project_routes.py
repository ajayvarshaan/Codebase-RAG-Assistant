from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database.database import get_db
from models.project import Project
from models.user import User
from services.auth_dependency import get_current_user


router = APIRouter(
    prefix="/projects",
    tags=["Projects"]
)


# =========================================================
# CREATE PROJECT
# =========================================================

@router.post("/")
def create_project(
    name: str,
    description: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    project = Project(
        user_id=current_user.id,
        name=name,
        description=description
    )

    db.add(project)
    db.commit()
    db.refresh(project)

    return {
        "id": project.id,
        "user_id": project.user_id,
        "name": project.name,
        "description": project.description,
        "created_at": project.created_at
    }


# =========================================================
# GET MY PROJECTS
# =========================================================

@router.get("/")
def get_projects(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    projects = (
        db.query(Project)
        .filter(
            Project.user_id == current_user.id
        )
        .order_by(Project.id)
        .all()
    )

    return projects


# =========================================================
# GET ONE PROJECT
# =========================================================

@router.get("/{project_id}")
def get_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
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

    return project