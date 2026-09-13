from sqlalchemy.orm import Session

from models.code_file import CodeFile
from services.generation_service import generate_answer


def generate_test_cases(
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
File for test case generation:

{code_file.file_path}

Code:

{code_file.content}
"""

    question = f"""
Generate practical test cases for the following code file:

{code_file.file_path}

Create tests based only on the provided code.

Include:

1. What functionality should be tested.
2. Normal or happy-path test cases.
3. Edge cases and boundary cases.
4. Invalid input or error cases, when applicable.
5. Expected result for each test case.
6. Important mocks, setup, or test data that may be needed.
7. A short list of the highest-priority tests to implement first.

If the file is a hook, component, utility, class, or API-related file, tailor the test cases to that type.

Do not invent functionality that is not present in the code.

Use clear Markdown headings and a table when useful.
"""

    answer = generate_answer(
        question=question,
        context=context,
        conversation_history=""
    )

    return answer