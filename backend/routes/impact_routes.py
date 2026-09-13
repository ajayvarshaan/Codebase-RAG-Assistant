from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database.database import SessionLocal
from models.project import Project
from models.code_file import CodeFile

from services.impact_service import get_impact_analysis


router = APIRouter(
    prefix="/impact",
    tags=["Impact Analysis"]
)


def get_db():
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()


@router.get("/project/{project_id}/file/{file_id}")
def analyze_file_impact(
    project_id: int,
    file_id: int,
    db: Session = Depends(get_db)
):

    # Check project

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


    # Check file

    code_file = (
        db.query(CodeFile)
        .filter(
            CodeFile.id == file_id,
            CodeFile.project_id == project_id
        )
        .first()
    )

    if not code_file:
        raise HTTPException(
            status_code=404,
            detail="Code file not found"
        )


    # Find affected files

    affected_files = get_impact_analysis(
        db=db,
        file_id=file_id,
        project_id=project_id
    )


    return {
        "project_id": project_id,
        "file_id": file_id,
        "file_path": code_file.file_path,
        "affected_files": affected_files
    }