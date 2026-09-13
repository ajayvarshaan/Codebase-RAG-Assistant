from fastapi import APIRouter

from services.test_runner_service import run_automated_tests


router = APIRouter(
    prefix="/tests",
    tags=["Automated Tests"]
)


@router.get("/run")
def run_tests():
    return run_automated_tests()
