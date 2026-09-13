from sqlalchemy.orm import Session

from models.code_file import CodeFile
from models.code_relationship import CodeRelationship

from services.generation_service import generate_answer


def generate_architecture_summary(
    db: Session,
    project_id: int
):
    files = (
        db.query(CodeFile)
        .filter(
            CodeFile.project_id == project_id
        )
        .order_by(CodeFile.file_path)
        .all()
    )

    relationships = (
        db.query(CodeRelationship)
        .filter(
            CodeRelationship.project_id == project_id
        )
        .all()
    )

    if not files:
        return "No code files have been indexed for this project."

    file_map = {
        code_file.id: code_file.file_path
        for code_file in files
    }

    context_parts = []

    context_parts.append(
        "PROJECT FILES:\n"
    )

    for code_file in files:
        context_parts.append(
            f"""
File: {code_file.file_path}

Code:
{code_file.content}
"""
        )

    context_parts.append(
        "\nCODE RELATIONSHIPS:\n"
    )

    if relationships:
        for relationship in relationships:
            source_path = file_map.get(
                relationship.source_file_id,
                "Unknown file"
            )

            target_path = file_map.get(
                relationship.target_file_id,
                "Unknown file"
            )

            context_parts.append(
                f"{source_path} --{relationship.relationship_type}--> {target_path}"
            )
    else:
        context_parts.append(
            "No code relationships were detected."
        )

    context = "\n".join(context_parts)

    question = """
Create a clear architecture overview of this codebase.

Explain:

1. What the project appears to do.
2. The main files and their responsibilities.
3. How the files are connected.
4. Important dependency relationships.
5. The main execution or data flow you can infer.
6. Which files appear to be reusable utilities, components, configuration, or entry points.
7. A short practical summary for a developer who is new to this project.

Use only the provided project files and relationships.
Do not invent files, functionality, or dependencies.
If something cannot be determined from the provided code, say so.

Use Markdown headings and bullet points to make the explanation easy to read.
"""

    return generate_answer(
        question=question,
        context=context,
        conversation_history=""
    )