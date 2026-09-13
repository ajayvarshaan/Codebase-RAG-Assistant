from sqlalchemy.orm import Session

from models.code_file import CodeFile
from services.generation_service import generate_answer


def generate_file_explanation(
    db: Session,
    file_id: int,
    project_id: int
):
    code_file = (
        db.query(CodeFile)
        .filter(
            CodeFile.id == file_id,
            CodeFile.project_id == project_id
        )
        .first()
    )

    if not code_file:
        return "Could not find the selected file."


    project_files = (
        db.query(CodeFile)
        .filter(
            CodeFile.project_id == project_id
        )
        .all()
    )


    context_parts = []


    # Selected file

    context_parts.append(
        f"""
SELECTED FILE:

File: {code_file.file_path}

Code:
{code_file.content}
"""
    )


    # Other project files

    context_parts.append(
        "\nOTHER PROJECT FILES:\n"
    )


    for project_file in project_files:

        if project_file.id == code_file.id:
            continue

        context_parts.append(
            f"""
File: {project_file.file_path}

Code:
{project_file.content}
"""
        )


    context = "\n".join(context_parts)


    question = f"""
Explain the file:

{code_file.file_path}

Analyze the provided code and explain:

1. Purpose of the file.
2. Main functions, classes, hooks, or components.
3. Important logic and how it works.
4. Dependencies used by this file.
5. How this file connects to the rest of the project.
6. Potential issues, risks, or things a developer should be careful about.
7. A short summary for a developer who is seeing this file for the first time.

Only use the provided code context.
Do not invent functionality that is not present in the code.

Use clear Markdown headings and bullet points.
"""


    answer = generate_answer(
        question=question,
        context=context,
        conversation_history=""
    )


    return answer