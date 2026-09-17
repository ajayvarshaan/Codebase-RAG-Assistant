from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database.database import SessionLocal
from models.project import Project
from models.code_file import CodeFile
from models.user import User

from services.auth_dependency import get_current_user
from services.file_explanation_service import generate_file_explanation


router = APIRouter(
    prefix="/file-explanation",
    tags=["File Explanation"]
)


def get_db():
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()


@router.get("/project/{project_id}/file/{file_id}")
def explain_file(
    project_id: int,
    file_id: int,
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
    # Check file
    # ---------------------------------------------------------

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


    # ---------------------------------------------------------
    # Generate AI explanation
    # ---------------------------------------------------------

    explanation = generate_file_explanation(
        db=db,
        file_id=file_id,
        project_id=project_id
    )


    # ---------------------------------------------------------
    # Return result
    # ---------------------------------------------------------

    return {
        "project_id": project_id,
        "file_id": file_id,
        "file_path": code_file.file_path,
        "explanation": explanation
    }