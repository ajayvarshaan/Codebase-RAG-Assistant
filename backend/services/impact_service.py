from sqlalchemy.orm import Session

from models.code_relationship import CodeRelationship
from models.code_file import CodeFile


def get_impact_analysis(
    db: Session,
    file_id: int,
    project_id: int
):
    affected_files = []
    visited = set()

    def find_importers(current_file_id: int):

        if current_file_id in visited:
            return

        visited.add(current_file_id)

        relationships = (
            db.query(CodeRelationship)
            .filter(
                CodeRelationship.project_id == project_id,
                CodeRelationship.target_file_id == current_file_id
            )
            .all()
        )

        for relationship in relationships:

            importer_file = (
                db.query(CodeFile)
                .filter(
                    CodeFile.id ==
                    relationship.source_file_id
                )
                .first()
            )

            if not importer_file:
                continue

            affected_files.append({
                "file_id": importer_file.id,
                "file_path": importer_file.file_path,
                "relationship": "imports"
            })

            find_importers(
                importer_file.id
            )

    find_importers(file_id)

    return affected_files