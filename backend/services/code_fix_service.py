from sqlalchemy.orm import Session

from models.code_file import CodeFile
from services.generation_service import generate_answer


def generate_code_fix(
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
File to improve:

{code_file.file_path}

Current code:

{code_file.content}
"""

    question = f"""
Analyze the following code file and suggest practical code fixes:

{code_file.file_path}

Your task is to identify concrete problems that are supported by the
provided code and propose an improved version.

For the response:

1. Start with a short summary of the most important problems found.
2. Explain why each problem matters.
3. Provide a complete improved version of the file when a meaningful fix
   can be proposed.
4. Clearly explain what changed in the improved code.
5. Preserve the existing functionality unless a change is necessary to fix
   a problem.
6. Do not invent missing files, APIs, requirements, or functionality.
7. If the current code is already reasonable, say so and suggest only
   improvements that are supported by the code.
8. Do not claim that the suggested code has been tested or executed.

Use clear Markdown headings and fenced code blocks.

Only use the provided code as the basis for the suggestions.
"""

    answer = generate_answer(
        question=question,
        context=context,
        conversation_history=""
    )

    return answer