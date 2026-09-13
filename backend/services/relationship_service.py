from sqlalchemy.orm import Session

from models.code_relationship import CodeRelationship
from models.code_file import CodeFile


def get_related_files(
    db: Session,
    file_id: int,
    project_id: int
):
    """
    Find files that are related to the given file.

    Currently we look for:
    - Files imported by this file
    - Files that import this file
    """

    relationships = (
        db.query(CodeRelationship)
        .filter(
            CodeRelationship.project_id == project_id,
            (
                (CodeRelationship.source_file_id == file_id)
                |
                (CodeRelationship.target_file_id == file_id)
            )
        )
        .all()
    )

    related_files = []

    for relationship in relationships:

        if relationship.source_file_id == file_id:
            related_file_id = relationship.target_file_id
            relationship_direction = "imports"

        else:
            related_file_id = relationship.source_file_id
            relationship_direction = "imported_by"

        related_file = (
            db.query(CodeFile)
            .filter(
                CodeFile.id == related_file_id
            )
            .first()
        )

        if not related_file:
            continue

        related_files.append({
            "file_id": related_file.id,
            "file_path": related_file.file_path,
            "relationship": relationship_direction
        })

    return related_files