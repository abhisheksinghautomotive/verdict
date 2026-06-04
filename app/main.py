import logging
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("verdict-app")

app = FastAPI(title="Verdict Test Runner", version="1.0.0")

# Module-level list to store results in-memory
TEST_RESULTS: list[dict[str, Any]] = []


class TestRunRequest(BaseModel):
    """Request model for running a test file."""

    test_file: str = Field(..., description="The path to the test file to run.")


class TestRunResponse(BaseModel):
    """Response model representing the test execution outcome."""

    status: str = Field(..., description="The result status: pass or fail.")
    stdout: str = Field(..., description="The standard output/error of the execution.")
    duration_ms: int = Field(..., description="The test duration in milliseconds.")


def resolve_test_path(test_file: str) -> Path:
    """Resolves and validates the path of the target test file.

    Handles paths specified relative to either the workspace root or the
    app directory itself.

    Args:
        test_file: The path to the test file.

    Returns:
        Path: The resolved Path object.
    """
    path = Path(test_file)
    if path.exists() and path.is_file():
        return path.resolve()

    # If running from inside 'app/' directory and path starts with 'app/'
    if test_file.startswith("app/") and Path(".").resolve().name == "app":
        stripped_path = Path(test_file[4:])
        if stripped_path.exists() and stripped_path.is_file():
            return stripped_path.resolve()

    # Try resolving relative to current working directory
    cwd_path = Path(".").resolve() / test_file
    if cwd_path.exists() and cwd_path.is_file():
        return cwd_path.resolve()

    return path


@app.post("/run-test", response_model=TestRunResponse)
def run_test(payload: TestRunRequest) -> dict[str, Any]:
    """Runs a specified pytest file using subprocess.

    Args:
        payload: The request body containing the test file path.

    Returns:
        dict: A dictionary containing status, stdout, and duration_ms.

    Raises:
        HTTPException: If the test file is not found or execution fails.
    """
    logger.info("Received request to run test file: %s", payload.test_file)
    resolved_path = resolve_test_path(payload.test_file)

    if not resolved_path.exists() or not resolved_path.is_file():
        logger.error("Test file not found: %s", payload.test_file)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Test file not found: {payload.test_file}",
        )

    logger.info("Executing pytest on resolved path: %s", resolved_path)
    start_time = time.perf_counter()

    try:
        # Run pytest via the current python interpreter to use correct env
        result = subprocess.run(
            [sys.executable, "-m", "pytest", str(resolved_path)],
            capture_output=True,
            text=True,
            check=False,
        )
    except Exception as exc:
        logger.exception("Failed to execute subprocess for %s", resolved_path)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Subprocess execution failed: {str(exc)}",
        ) from exc

    duration_ms = int((time.perf_counter() - start_time) * 1000)
    run_status = "pass" if result.returncode == 0 else "fail"

    # Merge stdout and stderr for full visibility
    stdout_output = result.stdout
    if result.stderr:
        stdout_output += f"\n--- STDERR ---\n{result.stderr}"

    logger.info(
        "Test execution finished. Status: %s, Duration: %d ms",
        run_status,
        duration_ms,
    )

    response_data = {
        "status": run_status,
        "stdout": stdout_output,
        "duration_ms": duration_ms,
    }

    # Store in module-level list
    TEST_RESULTS.append({"test_file": payload.test_file, **response_data})

    return response_data


@app.get("/health")
def health_check() -> dict[str, str]:
    """Liveness health check endpoint.

    Returns:
        dict: A dictionary containing status: ok.
    """
    return {"status": "ok"}


@app.get("/results")
def get_results() -> list[dict[str, Any]]:
    """Retrieves all test execution results run so far.

    Returns:
        list: A list of result records.
    """
    return TEST_RESULTS
