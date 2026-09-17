from sqlalchemy.orm import Session
from models.code_relationship import CodeRelationship
from models.code_file import CodeFile


def get_impact_analysis(db: Session, file_id: int, project_id: int):
    """
    Find files that directly or indirectly import the selected file.

    Performance optimization:
    - Load all project relationships once.
    - Load all project file metadata once.
    - Traverse the relationship graph in memory instead of querying
      PostgreSQL for every visited file.
    """
    relationships = (
        db.query(CodeRelationship)
        .filter(CodeRelationship.project_id == project_id)
        .all()
    )

    if not relationships:
        return []

    files = (
        db.query(CodeFile)
        .filter(CodeFile.project_id == project_id)
        .all()
    )

    file_map = {code_file.id: code_file for code_file in files}

    # target_file_id -> source_file_ids
    importers_map = {}
    for relationship in relationships:
        importers_map.setdefault(
            relationship.target_file_id,
            []
        ).append(relationship.source_file_id)

    affected_files = []
    visited = set()

    def find_importers(current_file_id: int):
        if current_file_id in visited:
            return

        visited.add(current_file_id)

        for importer_id in importers_map.get(current_file_id, []):
            importer_file = file_map.get(importer_id)
            if not importer_file:
                continue

            if importer_id != file_id:
                affected_files.append({
                    "file_id": importer_file.id,
                    "file_path": importer_file.file_path,
                    "relationship": "imports"
                })

            find_importers(importer_id)

    find_importers(file_id)

    return affected_files
