from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database.database import SessionLocal
from models.project import Project
from models.code_file import CodeFile
from models.code_relationship import CodeRelationship


router = APIRouter(
    prefix="/relationships",
    tags=["Relationships"]
)


def get_db():
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()


# ---------------------------------------------------------
# Get project file relationships
# ---------------------------------------------------------

@router.get("/project/{project_id}")
def get_project_relationships(
    project_id: int,
    db: Session = Depends(get_db)
):
    # Check project
    project = (
        db.query(Project)
        .filter(Project.id == project_id)
        .first()
    )

    if not project:
        raise HTTPException(
            status_code=404,
            detail="Project not found"
        )

    relationships = (
        db.query(CodeRelationship)
        .filter(
            CodeRelationship.project_id == project_id
        )
        .all()
    )

    result = []

    for relationship in relationships:

        source_file = (
            db.query(CodeFile)
            .filter(
                CodeFile.id
                == relationship.source_file_id
            )
            .first()
        )

        target_file = (
            db.query(CodeFile)
            .filter(
                CodeFile.id
                == relationship.target_file_id
            )
            .first()
        )

        if not source_file or not target_file:
            continue

        result.append({
            "id": relationship.id,
            "source_file_id": source_file.id,
            "source_file": source_file.file_path,
            "target_file_id": target_file.id,
            "target_file": target_file.file_path,
            "relationship_type": relationship.relationship_type
        })

    return {
        "project_id": project_id,
        "relationships": result
    }