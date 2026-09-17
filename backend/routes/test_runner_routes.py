from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database.database import SessionLocal
from models.project import Project
from models.user import User
from services.auth_dependency import get_current_user
from services.test_runner_service import (
    find_test_files,
    run_generated_test,
    run_project_tests
)
from models.code_file import CodeFile

router = APIRouter(
    prefix="/test-runner",
    tags=["Test Runner"]
)


class GeneratedTestRequest(BaseModel):
    test_code: str = Field(
        min_length=1,
        max_length=20000
    )

    test_file_name: str = Field(
        default="generated_ai_test.py",
        min_length=1,
        max_length=255
    )


def get_db():
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()


def get_owned_project(
    db: Session,
    project_id: int,
    current_user: User
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


@router.get("/project/{project_id}/tests")
def get_project_tests(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    get_owned_project(
        db,
        project_id,
        current_user
    )

    code_files = (
        db.query(CodeFile)
        .filter(
            CodeFile.project_id == project_id
        )
        .all()
    )

    tests = []

    for code_file in code_files:
        if code_file.file_path.replace(
            "\\",
            "/"
        ).lower().endswith(".py"):
            file_name = code_file.file_path.replace(
                "\\",
                "/"
            ).rsplit("/", 1)[-1].lower()

            if (
                file_name.startswith("test_")
                or file_name.endswith("_test.py")
            ):
                tests.append({
                    "file_id": code_file.id,
                    "file_path": code_file.file_path
                })

    tests.sort(
        key=lambda item: item["file_path"].lower()
    )

    return {
        "project_id": project_id,
        "count": len(tests),
        "tests": tests
    }


@router.post("/project/{project_id}")
def run_project_test_suite(
    project_id: int,
    test_path: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    get_owned_project(
        db,
        project_id,
        current_user
    )

    try:
        return run_project_tests(
            db=db,
            project_id=project_id,
            test_path=test_path
        )

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error)
        )

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Test execution failed: {str(error)}"
        )


@router.post("/project/{project_id}/generated")
def run_generated_project_test(
    project_id: int,
    request: GeneratedTestRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    get_owned_project(
        db,
        project_id,
        current_user
    )

    try:
        return run_generated_test(
            db=db,
            project_id=project_id,
            test_code=request.test_code,
            test_file_name=request.test_file_name
        )

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error)
        )

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=(
                "Generated test execution failed: "
                f"{str(error)}"
            )
        )
