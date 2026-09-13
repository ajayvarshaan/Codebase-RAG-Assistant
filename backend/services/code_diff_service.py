from sqlalchemy.orm import Session

from models.project import Project
from services.generation_service import generate_answer


def generate_code_diff_analysis(
    db: Session,
    project_id: int,
    file_name: str,
    old_code: str,
    new_code: str
):
    project = (
        db.query(Project)
        .filter(Project.id == project_id)
        .first()
    )

    if not project:
        return "Could not find the selected project."

    context = f"""
Project: {project.name}

File being changed: {file_name}

OLD CODE:
{old_code}

NEW CODE:
{new_code}
"""

    question = f"""
Analyze the code change for:

{file_name}

Compare the OLD CODE with the NEW CODE.

Explain:

1. What changed.
2. Which functionality or behavior changed.
3. Bugs, regressions, or risks that could be introduced.
4. Performance, security, error-handling, or maintainability concerns caused by the change, when supported by the code.
5. Which existing tests should be updated or added.
6. What parts of the application a developer should manually check after this change.
7. A short overall risk assessment: Low, Medium, or High, with a reason.

Only use the provided old and new code.
Do not invent files, dependencies, requirements, or behavior.
Do not claim that the code was executed or tested.

Use clear Markdown headings and bullet points.
"""

    return generate_answer(
        question=question,
        context=context,
        conversation_history=""
    )