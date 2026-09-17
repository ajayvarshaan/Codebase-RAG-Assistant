from pathlib import Path

from sqlalchemy.orm import Session

from models.code_file import CodeFile
from services.generation_service import generate_answer


def build_python_import_hint(
    file_path: str
) -> str:
    """
    Create an import hint for Python files so the AI knows
    exactly how the generated test should import the code
    under test.
    """

    normalized_path = file_path.replace(
        "\\",
        "/"
    )

    if not normalized_path.lower().endswith(
        ".py"
    ):
        return ""

    module_path = normalized_path[:-3]

    if module_path.endswith(
        "/__init__"
    ):
        module_path = module_path[:-9]

    module_name = module_path.replace(
        "/",
        "."
    )

    if not module_name:
        return ""

    return f"""
Python import information:

The code under test is located at:

{file_path}

The Python module import path is:

{module_name}

The generated executable test MUST import every
function or class that it tests from this module.

For example, if the source file is:

hello.py

and it contains:

def hello():
    return "Hello, World!"

the generated executable test MUST contain:

from hello import hello

def test_hello():
    assert hello() == "Hello, World!"

Do NOT call a function, class, variable, or object from
the source file without importing or defining it.
"""


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
        return (
            "Could not find the selected file."
        )

    python_import_hint = (
        build_python_import_hint(
            code_file.file_path
        )
    )

    context = f"""
File for test case generation:

{code_file.file_path}

Code:

{code_file.content}

{python_import_hint}
"""

    question = f"""
Generate practical test cases for the following code file:

{code_file.file_path}

Create tests based ONLY on the provided code.

Include:

1. What functionality should be tested.
2. Normal or happy-path test cases.
3. Edge cases and boundary cases.
4. Invalid input or error cases, when applicable.
5. Expected result for each test case.
6. Important mocks, setup, or test data that may be needed.
7. A short list of the highest-priority tests to implement first.

If the file is a hook, component, utility, class, or API-related
file, tailor the test cases to that type.

Do not invent functionality that is not present in the code.

IMPORTANT FOR EXECUTABLE PYTHON TESTS:

The final executable Python test MUST:

- Be directly runnable with pytest.
- Include every required import.
- Import every function/class/variable it tests.
- Never call an undefined name.
- Never assume that pytest automatically provides application functions.
- Use the correct Python module path based on the source file path.
- Use only functions, classes and variables that actually exist
  in the provided source code.
- Not contain fictional modules.
- Not contain fictional functions.
- Not contain placeholder imports.
- Not contain placeholder code.
- Include pytest only when pytest functionality is required.

For example, if the source file is:

hello.py

and contains:

def hello():
    return "Hello, World!"

the executable test MUST be:

from hello import hello

def test_hello():
    assert hello() == "Hello, World!"

The import is REQUIRED.

Do not produce:

def test_hello():
    assert hello() == "Hello, World!"

because hello is undefined unless it is imported.

At the end of your response, provide the executable test
implementation inside a Python code block.

Use this exact final section heading:

## Executable Test Code

Then provide the complete Python test code in a fenced code block.

Before generating the executable test, inspect the provided
source code carefully and determine the actual functions,
classes, methods, inputs, outputs and behavior.

Use clear Markdown headings and a table when useful.
"""

    answer = generate_answer(
        question=question,
        context=context,
        conversation_history=""
    )

    return answer