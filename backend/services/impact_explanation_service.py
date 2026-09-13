from sqlalchemy.orm import Session

from models.code_file import CodeFile

from services.generation_service import generate_answer


def generate_impact_explanation(
    db: Session,
    file_id: int,
    project_id: int,
    affected_files: list
):
    changed_file = (
        db.query(CodeFile)
        .filter(
            CodeFile.id == file_id,
            CodeFile.project_id == project_id
        )
        .first()
    )

    if not changed_file:
        return "Could not find the file being analyzed."

    context_parts = []

    context_parts.append(
        f"""
File being changed:
{changed_file.file_path}

Code:
{changed_file.content}
"""
    )

    for affected_file in affected_files:

        code_file = (
            db.query(CodeFile)
            .filter(
                CodeFile.id == affected_file["file_id"],
                CodeFile.project_id == project_id
            )
            .first()
        )

        if not code_file:
            continue

        context_parts.append(
            f"""
Potentially affected file:
{code_file.file_path}

Relationship:
{affected_file["relationship"]}

Code:
{code_file.content}
"""
        )

    context = "\n".join(context_parts)

    question = f"""
Explain the impact of changing {changed_file.file_path}.

Identify which parts of the potentially affected files depend
on the changed file.

Explain:
1. Why each file is affected.
2. What functionality could be impacted.
3. What a developer should check before changing the file.

Only use the provided code and relationships.
"""

    answer = generate_answer(
        question=question,
        context=context,
        conversation_history=""
    )

    return answer