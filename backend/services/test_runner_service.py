import re
import subprocess
import sys
import time
from pathlib import Path


def run_automated_tests():
    """Run the project's automated pytest suite and return a JSON-safe result."""
    backend_dir = Path(__file__).resolve().parents[1]
    tests_dir = backend_dir / "tests"

    if not tests_dir.exists():
        return {
            "success": False,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "total": 0,
            "duration_seconds": 0,
            "output": "No tests directory was found."
        }

    started = time.perf_counter()

    try:
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "pytest",
                "tests",
                "-q",
                "--disable-warnings"
            ],
            cwd=str(backend_dir),
            capture_output=True,
            text=True,
            timeout=60
        )
    except FileNotFoundError:
        return {
            "success": False,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "total": 0,
            "duration_seconds": round(time.perf_counter() - started, 2),
            "output": "pytest is not installed. Run: python -m pip install pytest"
        }
    except subprocess.TimeoutExpired as error:
        output = (error.stdout or "") + "\n" + (error.stderr or "")
        return {
            "success": False,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "total": 0,
            "duration_seconds": round(time.perf_counter() - started, 2),
            "output": "Test execution timed out after 60 seconds.\n\n" + output.strip()
        }

    output = (result.stdout or "")
    if result.stderr:
        output += "\n" + result.stderr

    passed = 0
    failed = 0
    skipped = 0

    match = re.search(r"(\d+) passed", output)
    if match:
        passed = int(match.group(1))

    match = re.search(r"(\d+) failed", output)
    if match:
        failed = int(match.group(1))

    match = re.search(r"(\d+) skipped", output)
    if match:
        skipped = int(match.group(1))

    total = passed + failed + skipped

    return {
        "success": result.returncode == 0,
        "passed": passed,
        "failed": failed,
        "skipped": skipped,
        "total": total,
        "duration_seconds": round(time.perf_counter() - started, 2),
        "output": output.strip()
    }
