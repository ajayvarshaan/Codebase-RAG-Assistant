from sqlalchemy.orm import Session

from models.code_file import CodeFile
from models.code_relationship import CodeRelationship
from models.project import Project

from services.generation_service import generate_answer


def generate_readme(
    db: Session,
    project_id: int
):
    project = (
        db.query(Project)
        .filter(Project.id == project_id)
        .first()
    )

    if not project:
        return "Could not find the selected project."

    files = (
        db.query(CodeFile)
        .filter(CodeFile.project_id == project_id)
        .order_by(CodeFile.file_path)
        .all()
    )

    relationships = (
        db.query(CodeRelationship)
        .filter(CodeRelationship.project_id == project_id)
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
        f"PROJECT NAME:\n{project.name}"
    )

    if project.description:
        context_parts.append(
            f"\nPROJECT DESCRIPTION:\n{project.description}"
        )

    context_parts.append("\nPROJECT FILES:")

    for code_file in files:
        context_parts.append(
            f"""
File: {code_file.file_path}

Code:
{code_file.content}
"""
        )

    context_parts.append("\nCODE RELATIONSHIPS:")

    if relationships:
        for relationship in relationships:
            source = file_map.get(
                relationship.source_file_id,
                "Unknown file"
            )
            target = file_map.get(
                relationship.target_file_id,
                "Unknown file"
            )

            context_parts.append(
                f"{source} --{relationship.relationship_type}--> {target}"
            )
    else:
        context_parts.append(
            "No code relationships were detected."
        )

    context = "\n".join(context_parts)

    question = f"""
Generate a professional README.md for the project:

{project.name}

Use only the provided project files, project description,
and detected relationships.

Include these sections when the available code supports them:

1. Project title and overview.
2. Features.
3. Technologies used.
4. Project structure.
5. Architecture and important dependencies.
6. Installation or setup instructions, but only when they
   can be inferred from provided configuration files.
7. Usage, but only when supported by the provided code.
8. Important development notes.
9. Limitations or information that cannot be determined.
10. A short conclusion.

Rules:

- Do not invent commands, environment variables,
  dependencies, APIs, or features.
- If installation or usage details cannot be determined,
  explicitly say that the information is not available
  in the provided project files.
- Use valid Markdown.
- Make the README practical and ready to save as README.md.
- Keep the explanation concise but useful.
"""

    return generate_answer(
        question=question,
        context=context,
        conversation_history=""
    )
