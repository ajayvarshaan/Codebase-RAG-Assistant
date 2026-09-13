from sqlalchemy.orm import Session

from models.code_file import CodeFile


def search_codebase(
    db: Session,
    project_id: int,
    query: str,
    max_results: int = 50
):
    query = query.strip()

    if not query:
        return []

    code_files = (
        db.query(CodeFile)
        .filter(
            CodeFile.project_id == project_id
        )
        .order_by(
            CodeFile.file_path
        )
        .all()
    )

    query_lower = query.lower()

    results = []

    for code_file in code_files:

        lines = code_file.content.splitlines()

        # -------------------------------------------------
        # Check whether the file name/path matches
        # -------------------------------------------------

        file_path_matches = (
            query_lower in code_file.file_path.lower()
        )

        # -------------------------------------------------
        # Search actual code lines
        # -------------------------------------------------

        for index, line in enumerate(lines):

            if query_lower in line.lower():

                results.append({
                    "file_id": code_file.id,
                    "file_path": code_file.file_path,
                    "line_number": index + 1,
                    "line_content": line.strip()
                })

                if len(results) >= max_results:
                    return results

        # -------------------------------------------------
        # If only the file path matched, add ONE result
        # -------------------------------------------------

        if file_path_matches:

            results.append({
                "file_id": code_file.id,
                "file_path": code_file.file_path,
                "line_number": 1,
                "line_content": f"File name/path matches: {code_file.file_path}"
            })

            if len(results) >= max_results:
                return results

    return results