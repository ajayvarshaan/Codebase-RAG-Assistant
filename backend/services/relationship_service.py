from sqlalchemy.orm import Session
from models.code_relationship import CodeRelationship
from models.code_file import CodeFile


def get_related_files(db: Session, file_id: int, project_id: int):
    """
    Return files related to the selected file.

    Performance optimization:
    - Fetch all matching relationships in one query.
    - Fetch all related CodeFile rows in one query instead of querying
      CodeFile once for every relationship.
    """
    relationships = (
        db.query(CodeRelationship)
        .filter(
            CodeRelationship.project_id == project_id,
            (
                (CodeRelationship.source_file_id == file_id)
                | (CodeRelationship.target_file_id == file_id)
            )
        )
        .all()
    )

    if not relationships:
        return []

    related_file_ids = set()
    for relationship in relationships:
        if relationship.source_file_id == file_id:
            related_file_ids.add(relationship.target_file_id)
        else:
            related_file_ids.add(relationship.source_file_id)

    files = (
        db.query(CodeFile)
        .filter(
            CodeFile.project_id == project_id,
            CodeFile.id.in_(related_file_ids)
        )
        .all()
    )

    file_map = {code_file.id: code_file for code_file in files}

    result = []
    for relationship in relationships:
        if relationship.source_file_id == file_id:
            related_file_id = relationship.target_file_id
            relationship_name = "imports"
        else:
            related_file_id = relationship.source_file_id
            relationship_name = "imported_by"

        related_file = file_map.get(related_file_id)
        if not related_file:
            continue

        result.append({
            "file_id": related_file.id,
            "file_path": related_file.file_path,
            "relationship": relationship_name
        })

    return result
