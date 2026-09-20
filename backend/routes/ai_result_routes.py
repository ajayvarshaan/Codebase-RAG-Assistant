import json

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Any
from sqlalchemy.orm import Session

from database.database import get_db
from models.project import Project
from models.user import User
from models.ai_result import AIResult
from services.auth_dependency import get_current_user


router = APIRouter(
    prefix="/ai-results",
    tags=["AI Results"],
)


class AIResultRequest(BaseModel):
    tool_name: str = Field(min_length=1, max_length=100)
    file_id: int | None = Field(default=None, gt=0)
    result: Any


@router.get("/project/{project_id}")
def get_ai_results(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = (
        db.query(Project)
        .filter(
            Project.id == project_id,
            Project.user_id == current_user.id,
        )
        .first()
    )

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    rows = (
        db.query(AIResult)
        .filter(AIResult.project_id == project_id)
        .order_by(AIResult.updated_at.desc(), AIResult.id.desc())
        .all()
    )

    results = []

    for row in rows:
        try:
            result = json.loads(row.result_json)
        except json.JSONDecodeError:
            result = row.result_json

        results.append({
            "id": row.id,
            "project_id": row.project_id,
            "file_id": row.file_id,
            "tool_name": row.tool_name,
            "result": result,
            "created_at": row.created_at,
            "updated_at": row.updated_at,
        })

    return {
        "project_id": project_id,
        "results": results,
    }


@router.post("/project/{project_id}")
def save_ai_result(
    project_id: int,
    request: AIResultRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = (
        db.query(Project)
        .filter(
            Project.id == project_id,
            Project.user_id == current_user.id,
        )
        .first()
    )

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if request.file_id is not None:
        from models.code_file import CodeFile

        file = (
            db.query(CodeFile)
            .filter(
                CodeFile.id == request.file_id,
                CodeFile.project_id == project_id,
            )
            .first()
        )

        if not file:
            raise HTTPException(status_code=404, detail="Code file not found")

    # Keep one latest result for each tool/file combination.
    existing = (
        db.query(AIResult)
        .filter(
            AIResult.project_id == project_id,
            AIResult.tool_name == request.tool_name,
            AIResult.file_id == request.file_id,
        )
        .first()
    )

    try:
        result_json = json.dumps(request.result, default=str)
    except (TypeError, ValueError) as error:
        raise HTTPException(
            status_code=400,
            detail=f"Could not store AI result: {error}",
        )

    if existing:
        existing.result_json = result_json
        db.commit()
        db.refresh(existing)
        row = existing
    else:
        row = AIResult(
            project_id=project_id,
            file_id=request.file_id,
            tool_name=request.tool_name,
            result_json=result_json,
        )
        db.add(row)
        db.commit()
        db.refresh(row)

    return {
        "message": "AI result saved successfully",
        "id": row.id,
        "project_id": row.project_id,
        "file_id": row.file_id,
        "tool_name": row.tool_name,
    }


@router.delete("/project/{project_id}")
def delete_project_ai_results(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = (
        db.query(Project)
        .filter(
            Project.id == project_id,
            Project.user_id == current_user.id,
        )
        .first()
    )

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    deleted = (
        db.query(AIResult)
        .filter(AIResult.project_id == project_id)
        .delete(synchronize_session=False)
    )

    db.commit()

    return {
        "message": "Project AI results cleared",
        "deleted": deleted,
    }


@router.delete("/project/{project_id}/tool/{tool_name}")
def delete_ai_tool_result(
    project_id: int,
    tool_name: str,
    file_id: int | None = Query(default=None, gt=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = (
        db.query(Project)
        .filter(
            Project.id == project_id,
            Project.user_id == current_user.id,
        )
        .first()
    )

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    query = db.query(AIResult).filter(
        AIResult.project_id == project_id,
        AIResult.tool_name == tool_name,
    )

    if file_id is None:
        query = query.filter(AIResult.file_id.is_(None))
    else:
        query = query.filter(AIResult.file_id == file_id)

    deleted = query.delete(synchronize_session=False)
    db.commit()

    return {
        "message": "AI result cleared",
        "deleted": deleted,
    }
