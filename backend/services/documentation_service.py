from sqlalchemy.orm import Session

from models.code_file import CodeFile
from services.generation_service import generate_answer


def generate_file_documentation(
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
File to document:

{code_file.file_path}

Code:

{code_file.content}
"""

    question = f"""
Generate developer documentation for this file:

{code_file.file_path}

Analyze only the provided code and create clear, practical documentation.

Include:

1. Purpose
2. Main functions, classes, hooks, or components
3. Important parameters, inputs, and outputs
4. How the main logic works
5. Dependencies used by the file
6. How the file is expected to be used
7. Important behavior, limitations, or things developers should know
8. A short example of usage when it can be directly inferred from the code

Use Markdown headings and bullet points.
Do not invent APIs, behavior, dependencies, or usage that are not supported by the code.
If something cannot be determined from the code, say so.
"""

    return generate_answer(
        question=question,
        context=context,
        conversation_history=""
    )
