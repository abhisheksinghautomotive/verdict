import contextvars
from contextlib import asynccontextmanager
from datetime import datetime, timezone
import logging
from pathlib import Path
import subprocess
import sys
import time
from typing import Any, Awaitable, Callable
import uuid

from fastapi import FastAPI, HTTPException, Request, Response, status
from pydantic import BaseModel, Field
from pythonjsonlogger import json

# Context variable to hold the request ID
request_id_var: contextvars.ContextVar[str] = contextvars.ContextVar(
    "request_id", default=""
)


class VerdictJsonFormatter(json.JsonFormatter):
    """Custom JSON formatter to structure logs with verdict metadata."""

    def add_fields(
        self,
        log_record: dict[str, Any],
        record: logging.LogRecord,
        message_dict: dict[str, Any],
    ) -> None:
        super().add_fields(log_record, record, message_dict)

        # Format timestamp to ISO 8601 UTC
        if "asctime" in log_record:
            log_record["timestamp"] = log_record.pop("asctime")
        else:
            log_record["timestamp"] = datetime.fromtimestamp(
                record.created, tz=timezone.utc
            ).isoformat()

        # Set level, service name, and request_id
        log_record["level"] = record.levelname
        log_record.pop("levelname", None)
        log_record["service"] = "verdict-app"

        req_id = request_id_var.get()
        if req_id:
            log_record["request_id"] = req_id


def setup_logging() -> None:
    """Configures structured JSON logging for the root logger and redirects Uvicorn loggers."""
    root_logger = logging.getLogger()

    # Remove all existing handlers
    for handler in list(root_logger.handlers):
        root_logger.removeHandler(handler)

    # Create stream handler
    json_handler = logging.StreamHandler(sys.stdout)
    formatter = VerdictJsonFormatter("%(asctime)s %(levelname)s %(name)s %(message)s")
    json_handler.setFormatter(formatter)

    # Configure root logger
    root_logger.addHandler(json_handler)
    root_logger.setLevel(logging.INFO)

    # Configure uvicorn loggers to propagate to the root logger
    for logger_name in ["uvicorn", "uvicorn.access", "uvicorn.error"]:
        uv_logger = logging.getLogger(logger_name)
        uv_logger.propagate = True
        for handler in list(uv_logger.handlers):
            uv_logger.removeHandler(handler)


# Initialize logging immediately on import
setup_logging()
logger = logging.getLogger("verdict-app")


@asynccontextmanager
async def lifespan(app: FastAPI) -> Any:
    """Lifespan event handler to set up JSON logging on startup."""
    setup_logging()
    yield


app = FastAPI(title="Verdict Test Runner", version="1.0.0", lifespan=lifespan)


@app.middleware("http")
async def log_requests(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    """FastAPI middleware to inject request_id and log request details."""
    req_id = str(uuid.uuid4())
    token = request_id_var.set(req_id)
    start_time = time.perf_counter()

    try:
        response = await call_next(request)
        duration_ms = int((time.perf_counter() - start_time) * 1000)
        logger.info(
            "request_completed",
            extra={
                "path": request.url.path,
                "status": response.status_code,
                "duration_ms": duration_ms,
            },
        )
        return response
    except Exception as exc:
        duration_ms = int((time.perf_counter() - start_time) * 1000)
        logger.error(
            "request_failed",
            extra={
                "path": request.url.path,
                "status": 500,
                "duration_ms": duration_ms,
                "error": str(exc),
            },
        )
        raise exc
    finally:
        request_id_var.reset(token)


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
