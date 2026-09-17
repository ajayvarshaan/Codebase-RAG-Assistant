from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database.database import SessionLocal
from models.project import Project
from models.user import User

from services.auth_dependency import get_current_user
from services.code_diff_service import generate_code_diff_analysis


router = APIRouter(
    prefix="/code-diff",
    tags=["Code Diff Analysis"]
)


class CodeDiffRequest(BaseModel):
    file_name: str = "Selected file"
    old_code: str
    new_code: str


def get_db():
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()


@router.post("/project/{project_id}")
def analyze_code_diff(
    project_id: int,
    diff_data: CodeDiffRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    # Check project ownership
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

    # Validate old code
    if not diff_data.old_code.strip():
        raise HTTPException(
            status_code=400,
            detail="Old code cannot be empty"
        )

    # Validate new code
    if not diff_data.new_code.strip():
        raise HTTPException(
            status_code=400,
            detail="New code cannot be empty"
        )

    # Generate AI diff analysis
    file_name = diff_data.file_name.strip() or "Selected file"

    analysis = generate_code_diff_analysis(
        db=db,
        project_id=project_id,
        file_name=file_name,
        old_code=diff_data.old_code,
        new_code=diff_data.new_code
    )

    return {
        "project_id": project_id,
        "file_name": file_name,
        "analysis": analysis
    }