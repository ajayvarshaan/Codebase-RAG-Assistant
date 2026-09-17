import ast
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from sqlalchemy.orm import Session

from models.code_file import CodeFile


# ============================================================
# CONFIGURATION
# ============================================================

TEST_TIMEOUT_SECONDS = 60
MAX_OUTPUT_LENGTH = 20000

PYTHON_EXTENSIONS = (".py",)


# ============================================================
# PYTHON TEST FILE DETECTION
# ============================================================

def is_python_test_file(file_path: str) -> bool:

    path = file_path.replace("\\", "/").lower()

    if not path.endswith(".py"):
        return False

    file_name = path.rsplit("/", 1)[-1]

    return (
        file_name.startswith("test_")
        or file_name.endswith("_test.py")
    )


def find_test_files(
    code_files: list[CodeFile]
) -> list[str]:
    """
    Find all Python test files in the project.
    """

    return [
        code_file.file_path
        for code_file in code_files
        if is_python_test_file(
            code_file.file_path
        )
    ]


# ============================================================
# PATH VALIDATION
# ============================================================

def validate_relative_path(
    file_path: str
) -> Path:

    normalized = (
        file_path
        .replace("\\", "/")
        .strip()
    )

    if not normalized:
        raise ValueError(
            "File path cannot be empty."
        )

    path = Path(normalized)

    if path.is_absolute():
        raise ValueError(
            "Absolute file paths are not allowed."
        )

    if ".." in path.parts:
        raise ValueError(
            "Parent-directory paths are not allowed."
        )

    if normalized.startswith("/"):
        raise ValueError(
            "Root paths are not allowed."
        )

    return path


# ============================================================
# WRITE PROJECT FILES
# ============================================================

def write_project_files(
    project_dir: Path,
    code_files: list[CodeFile]
):
    """
    Recreate the indexed project inside a
    temporary directory.
    """

    for code_file in code_files:

        relative_path = validate_relative_path(
            code_file.file_path
        )

        destination = (
            project_dir / relative_path
        )

        destination.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        destination.write_text(
            code_file.content or "",
            encoding="utf-8"
        )


# ============================================================
# OUTPUT LIMITING
# ============================================================

def truncate_output(
    value: str
) -> str:

    if not value:
        return ""

    if len(value) <= MAX_OUTPUT_LENGTH:
        return value

    return (
        value[:MAX_OUTPUT_LENGTH]
        + "\n\n[Output truncated]"
    )


# ============================================================
# RUN PYTEST
# ============================================================

def run_pytest(
    project_dir: Path,
    test_path: str | None = None
):

    if test_path:

        relative_test_path = (
            validate_relative_path(
                test_path
            )
        )

        target = (
            project_dir
            / relative_test_path
        )

        if not target.exists():
            raise ValueError(
                f"Test file not found: {test_path}"
            )

        if not target.is_file():
            raise ValueError(
                f"Test path is not a file: {test_path}"
            )

        pytest_target = str(
            relative_test_path
        )

    else:

        pytest_target = "."

    command = [
        sys.executable,
        "-m",
        "pytest",
        pytest_target,
        "-q",
        "--disable-warnings",
        "--maxfail=20"
    ]

    started_at = time.perf_counter()

    environment = os.environ.copy()

    # Prevent user-site packages from interfering.
    environment["PYTHONNOUSERSITE"] = "1"

    # Make temporary project importable.
    existing_pythonpath = (
        environment.get(
            "PYTHONPATH",
            ""
        )
    )

    if existing_pythonpath:

        environment["PYTHONPATH"] = (
            str(project_dir)
            + os.pathsep
            + existing_pythonpath
        )

    else:

        environment["PYTHONPATH"] = (
            str(project_dir)
        )

    try:

        process = subprocess.run(
            command,
            cwd=str(project_dir),
            capture_output=True,
            text=True,
            timeout=TEST_TIMEOUT_SECONDS,
            env=environment
        )

    except subprocess.TimeoutExpired as error:

        duration = (
            time.perf_counter()
            - started_at
        )

        stdout = (
            error.stdout.decode(
                errors="replace"
            )
            if isinstance(
                error.stdout,
                bytes
            )
            else (
                error.stdout or ""
            )
        )

        stderr = (
            error.stderr.decode(
                errors="replace"
            )
            if isinstance(
                error.stderr,
                bytes
            )
            else (
                error.stderr or ""
            )
        )

        output = (
            f"{stdout}\n{stderr}"
        ).strip()

        return {
            "status": "timeout",
            "message": (
                "Tests exceeded the "
                f"{TEST_TIMEOUT_SECONDS}-second "
                "timeout."
            ),
            "duration_seconds": round(
                duration,
                3
            ),
            "test_files": [],
            "stdout": truncate_output(
                stdout
            ),
            "stderr": truncate_output(
                stderr
            ),
            "return_code": None,
            "output": truncate_output(
                output
            )
        }

    duration = (
        time.perf_counter()
        - started_at
    )

    stdout = process.stdout or ""
    stderr = process.stderr or ""

    stdout = truncate_output(
        stdout
    )

    stderr = truncate_output(
        stderr
    )

    combined_output = (
        f"{stdout}\n{stderr}"
    ).strip()

    # ========================================================
    # PASS
    # ========================================================

    if process.returncode == 0:

        status = "passed"

        message = (
            "All tests passed successfully."
        )

    # ========================================================
    # NO TESTS
    # ========================================================

    elif process.returncode == 5:

        status = "no_tests"

        message = (
            "No tests were collected."
        )

    # ========================================================
    # FAILURE
    # ========================================================

    else:

        status = "failed"

        message = (
            "One or more tests failed."
        )

    return {
        "status": status,
        "message": message,
        "duration_seconds": round(
            duration,
            3
        ),
        "test_files": [],
        "stdout": stdout,
        "stderr": stderr,
        "return_code": process.returncode,
        "output": truncate_output(
            combined_output
        )
    }


# ============================================================
# RUN EXISTING PROJECT TESTS
# ============================================================

def run_project_tests(
    db: Session,
    project_id: int,
    test_path: str | None = None
):

    code_files = (
        db.query(CodeFile)
        .filter(
            CodeFile.project_id == project_id
        )
        .all()
    )

    if not code_files:

        return {
            "status": "no_tests",
            "message": (
                "This project has no indexed files."
            ),
            "duration_seconds": 0,
            "test_files": [],
            "stdout": "",
            "stderr": "",
            "return_code": None,
            "output": ""
        }

    test_files = find_test_files(
        code_files
    )

    if not test_files:

        return {
            "status": "no_tests",
            "message": (
                "No Python test files were "
                "found in this project."
            ),
            "duration_seconds": 0,
            "test_files": [],
            "stdout": "",
            "stderr": "",
            "return_code": None,
            "output": ""
        }

    if test_path:

        normalized_test_path = (
            test_path
            .replace("\\", "/")
        )

        normalized_test_files = {
            path.replace("\\", "/")
            for path in test_files
        }

        if (
            normalized_test_path
            not in normalized_test_files
        ):

            raise ValueError(
                "Test file is not a discovered "
                f"Python test file: "
                f"{test_path}"
            )

    temp_dir = Path(
        tempfile.mkdtemp(
            prefix=(
                f"codebase_rag_test_"
                f"{project_id}_"
            )
        )
    )

    try:

        write_project_files(
            temp_dir,
            code_files
        )

        result = run_pytest(
            temp_dir,
            test_path=test_path
        )

        result["test_files"] = (
            test_files
        )

        return result

    finally:

        shutil.rmtree(
            temp_dir,
            ignore_errors=True
        )


# ============================================================
# EXTRACT GENERATED TEST CODE
# ============================================================

def extract_code_from_generated_test(
    test_code: str
) -> str:

    if (
        not test_code
        or not test_code.strip()
    ):

        raise ValueError(
            "Generated test code cannot be empty."
        )

    text = test_code.strip()

    fenced_matches = re.findall(
        r"```(?:python|py)?\s*\n?(.*?)```",
        text,
        flags=(
            re.IGNORECASE
            | re.DOTALL
        )
    )

    if fenced_matches:

        python_blocks = [
            block.strip()
            for block in fenced_matches
            if block.strip()
        ]

        if python_blocks:

            return max(
                python_blocks,
                key=len
            )

    return text


# ============================================================
# PYTHON SYMBOL DETECTION
# ============================================================

def get_python_symbols(
    code: str
) -> set[str]:
    """
    Find top-level functions, classes
    and variables defined in a Python file.
    """

    symbols: set[str] = set()

    try:

        tree = ast.parse(code)

    except SyntaxError:

        return symbols

    for node in tree.body:

        # Functions
        if isinstance(
            node,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef,
                ast.ClassDef
            )
        ):

            symbols.add(
                node.name
            )

        # Variables
        elif isinstance(
            node,
            (
                ast.Assign,
                ast.AnnAssign,
                ast.AugAssign
            )
        ):

            if isinstance(
                node,
                ast.Assign
            ):

                for target in node.targets:

                    if isinstance(
                        target,
                        ast.Name
                    ):

                        symbols.add(
                            target.id
                        )

            elif isinstance(
                node,
                ast.AnnAssign
            ):

                if isinstance(
                    node.target,
                    ast.Name
                ):

                    symbols.add(
                        node.target.id
                    )

            elif isinstance(
                node,
                ast.AugAssign
            ):

                if isinstance(
                    node.target,
                    ast.Name
                ):

                    symbols.add(
                        node.target.id
                    )

    return symbols


# ============================================================
# LOADED NAMES
# ============================================================

def get_loaded_python_names(
    code: str
) -> set[str]:
    """
    Find names used by the generated test.
    """

    names: set[str] = set()

    try:

        tree = ast.parse(code)

    except SyntaxError:

        return names

    for node in ast.walk(tree):

        if isinstance(
            node,
            ast.Name
        ):

            if isinstance(
                node.ctx,
                ast.Load
            ):

                names.add(
                    node.id
                )

    return names


# ============================================================
# IMPORTED NAMES
# ============================================================

def get_imported_names(
    code: str
) -> set[str]:
    """
    Find names already imported
    by the generated test.
    """

    imported: set[str] = set()

    try:

        tree = ast.parse(code)

    except SyntaxError:

        return imported

    for node in tree.body:

        # import module
        if isinstance(
            node,
            ast.Import
        ):

            for alias in node.names:

                imported.add(
                    alias.asname
                    or alias.name.split(".")[0]
                )

        # from module import name
        elif isinstance(
            node,
            ast.ImportFrom
        ):

            for alias in node.names:

                if alias.name == "*":
                    continue

                imported.add(
                    alias.asname
                    or alias.name
                )

    return imported


# ============================================================
# TEST-DEFINED NAMES
# ============================================================

def get_defined_test_names(
    code: str
) -> set[str]:
    """
    Find names directly defined
    inside the generated test.
    """

    defined: set[str] = set()

    try:

        tree = ast.parse(code)

    except SyntaxError:

        return defined

    for node in tree.body:

        if isinstance(
            node,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef,
                ast.ClassDef
            )
        ):

            defined.add(
                node.name
            )

        elif isinstance(
            node,
            ast.Assign
        ):

            for target in node.targets:

                if isinstance(
                    target,
                    ast.Name
                ):

                    defined.add(
                        target.id
                    )

        elif isinstance(
            node,
            ast.AnnAssign
        ):

            if isinstance(
                node.target,
                ast.Name
            ):

                defined.add(
                    node.target.id
                )

    return defined


# ============================================================
# BUILD PYTHON MODULE PATH
# ============================================================

def build_python_module_path(
    file_path: str
) -> str | None:
    """
    Convert:

        hello.py

    into:

        hello

    Convert:

        utils/helper.py

    into:

        utils.helper
    """

    normalized = (
        file_path
        .replace("\\", "/")
        .strip("/")
    )

    if not normalized.lower().endswith(
        ".py"
    ):
        return None

    module_path = normalized[:-3]

    # Remove /__init__
    if module_path.endswith(
        "/__init__"
    ):

        module_path = (
            module_path[:-9]
        )

    module_path = (
        module_path.replace(
            "/",
            "."
        )
    )

    if not module_path:
        return None

    return module_path


# ============================================================
# FIND SOURCE SYMBOLS
# ============================================================

def find_source_symbols_used_by_test(
    generated_code: str,
    code_files: list[CodeFile]
) -> list[tuple[str, str, str]]:
    """
    Find project source symbols used by
    the generated test but not imported.

    Returns:

        (
            symbol,
            module_path,
            source_file_path
        )
    """

    loaded_names = (
        get_loaded_python_names(
            generated_code
        )
    )

    imported_names = (
        get_imported_names(
            generated_code
        )
    )

    defined_names = (
        get_defined_test_names(
            generated_code
        )
    )

    # Built-in names and common testing names
    ignored_names = {
        "True",
        "False",
        "None",

        "print",
        "len",
        "str",
        "int",
        "float",
        "list",
        "dict",
        "set",
        "tuple",
        "bool",

        "range",
        "enumerate",
        "zip",
        "sum",
        "min",
        "max",
        "abs",
        "round",

        "open",
        "isinstance",
        "type",

        "Exception",
        "ValueError",
        "TypeError",
        "KeyError",
        "IndexError",

        "pytest"
    }

    missing_names = (
        loaded_names
        - imported_names
        - defined_names
        - ignored_names
    )

    if not missing_names:
        return []

    source_symbols: dict[
        str,
        list[tuple[str, str]]
    ] = {}

    # --------------------------------------------------------
    # Scan all Python source files.
    # --------------------------------------------------------

    for code_file in code_files:

        if not code_file.file_path.lower().endswith(
            PYTHON_EXTENSIONS
        ):
            continue

        module_path = (
            build_python_module_path(
                code_file.file_path
            )
        )

        if not module_path:
            continue

        symbols = get_python_symbols(
            code_file.content or ""
        )

        for symbol in symbols:

            source_symbols.setdefault(
                symbol,
                []
            ).append(
                (
                    module_path,
                    code_file.file_path
                )
            )

    matches: list[
        tuple[str, str, str]
    ] = []

    # --------------------------------------------------------
    # Only repair unambiguous symbols.
    # --------------------------------------------------------

    for name in sorted(
        missing_names
    ):

        locations = (
            source_symbols.get(
                name,
                []
            )
        )

        # Exactly one source file must
        # define the symbol.
        if len(locations) == 1:

            module_path, source_path = (
                locations[0]
            )

            matches.append(
                (
                    name,
                    module_path,
                    source_path
                )
            )

    return matches


# ============================================================
# REPAIR GENERATED PYTHON TEST
# ============================================================

def repair_generated_python_test(
    generated_code: str,
    code_files: list[CodeFile]
) -> str:
    """
    Automatically add missing imports.

    Example:

        def test_hello():
            assert hello() == "Hello, World!"

    becomes:

        from hello import hello

        def test_hello():
            assert hello() == "Hello, World!"
    """

    matches = (
        find_source_symbols_used_by_test(
            generated_code,
            code_files
        )
    )

    if not matches:
        return generated_code.strip()

    existing_imports = (
        get_imported_names(
            generated_code
        )
    )

    imports_to_add: list[str] = []

    for (
        symbol,
        module_path,
        _source_path
    ) in matches:

        if symbol in existing_imports:
            continue

        imports_to_add.append(
            f"from {module_path} "
            f"import {symbol}"
        )

    if not imports_to_add:
        return generated_code.strip()

    # Remove duplicates while preserving order.
    unique_imports = list(
        dict.fromkeys(
            imports_to_add
        )
    )

    import_block = (
        "\n".join(
            unique_imports
        )
        + "\n\n"
    )

    return (
        import_block
        + generated_code.strip()
    )


# ============================================================
# RUN GENERATED AI TEST
# ============================================================

def run_generated_test(
    db: Session,
    project_id: int,
    test_code: str,
    test_file_name: str = (
        "generated_ai_test.py"
    )
):

    # --------------------------------------------------------
    # Load project files.
    # --------------------------------------------------------

    code_files = (
        db.query(CodeFile)
        .filter(
            CodeFile.project_id
            == project_id
        )
        .all()
    )

    if not code_files:

        raise ValueError(
            "This project has no indexed files."
        )

    # --------------------------------------------------------
    # Extract executable Python.
    # --------------------------------------------------------

    generated_code = (
        extract_code_from_generated_test(
            test_code
        )
    )

    # --------------------------------------------------------
    # Automatically repair missing imports.
    # --------------------------------------------------------

    generated_code = (
        repair_generated_python_test(
            generated_code,
            code_files
        )
    )

    # --------------------------------------------------------
    # Validate generated test filename.
    # --------------------------------------------------------

    safe_name = Path(
        test_file_name
    ).name

    if (
        safe_name != test_file_name
        or not safe_name.endswith(".py")
        or safe_name in {
            ".",
            ".."
        }
    ):

        raise ValueError(
            "Generated test filename must "
            "be a simple .py filename."
        )

    # --------------------------------------------------------
    # Validate generated test size.
    # --------------------------------------------------------

    if (
        len(generated_code)
        > MAX_OUTPUT_LENGTH
    ):

        raise ValueError(
            "Generated test code is too large."
        )

    # --------------------------------------------------------
    # Create temporary project.
    # --------------------------------------------------------

    temp_dir = Path(
        tempfile.mkdtemp(
            prefix=(
                "codebase_rag_"
                "generated_test_"
                f"{project_id}_"
            )
        )
    )

    try:

        # ----------------------------------------------------
        # Write original project files.
        # ----------------------------------------------------

        write_project_files(
            temp_dir,
            code_files
        )

        # ----------------------------------------------------
        # Create generated test file.
        # ----------------------------------------------------

        generated_test_path = (
            temp_dir / safe_name
        )

        generated_test_path.write_text(
            generated_code,
            encoding="utf-8"
        )

        # ----------------------------------------------------
        # Execute generated test.
        # ----------------------------------------------------

        result = run_pytest(
            temp_dir,
            test_path=safe_name
        )

        # ----------------------------------------------------
        # Add generated-test metadata.
        # ----------------------------------------------------

        result["test_files"] = [
            safe_name
        ]

        result["generated_test"] = True

        result["generated_test_code"] = (
            generated_code
        )

        return result

    finally:

        # ----------------------------------------------------
        # Always remove temporary directory.
        # ----------------------------------------------------

        shutil.rmtree(
            temp_dir,
            ignore_errors=True
        )