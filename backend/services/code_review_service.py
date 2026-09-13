from sqlalchemy.orm import Session

from models.code_file import CodeFile
from services.generation_service import generate_answer


def generate_code_review(
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

    context = f"""
File being reviewed:

{code_file.file_path}

Code:

{code_file.content}
"""

    question = f"""
Review the following code file:

{code_file.file_path}

Perform a practical code review.

Analyze:

1. Bugs or possible incorrect behavior.
2. Code smells and maintainability problems.
3. Security concerns.
4. Performance concerns.
5. Error handling issues.
6. Readability and structure.
7. Specific improvement suggestions.

For every issue you identify:

- Explain the problem clearly.
- Mention the relevant code or logic.
- Explain why it could be a problem.
- Suggest a practical improvement.

If there are no issues in a category, say so.

Do not invent problems that are not supported by the provided code.

Use clear Markdown headings and bullet points.

End with a short overall assessment of the file.
"""

    answer = generate_answer(
        question=question,
        context=context,
        conversation_history=""
    )

    return answer