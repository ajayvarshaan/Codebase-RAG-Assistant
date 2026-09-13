from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database.database import SessionLocal
from models.project import Project
from models.code_file import CodeFile

from services.code_fix_service import generate_code_fix


router = APIRouter(
    prefix="/code-fix",
    tags=["AI Code Fix"]
)


def get_db():
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()


@router.get("/project/{project_id}/file/{file_id}")
def fix_file(
    project_id: int,
    file_id: int,
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

    fix = generate_code_fix(
        db=db,
        file_id=file_id,
        project_id=project_id
    )

    return {
        "project_id": project_id,
        "file_id": file_id,
        "file_path": code_file.file_path,
        "fix": fix
    }