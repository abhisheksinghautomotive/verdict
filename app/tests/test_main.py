import json
import logging
import subprocess
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import (
    TEST_RESULTS,
    VerdictJsonFormatter,
    app,
    request_id_var,
    load_application_secrets,
)

client = TestClient(app)


@pytest.fixture(autouse=True)
def clear_results() -> None:
    """Fixture to clear the module-level TEST_RESULTS list for test isolation."""
    TEST_RESULTS.clear()


def test_health_check() -> None:
    """Tests the /health endpoint for 200 OK status."""
    # Trigger PR gate execution validation
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_get_results_empty() -> None:
    """Tests /results returns empty list initially."""
    response = client.get("/results")
    assert response.status_code == 200
    assert response.json() == []


def test_run_test_not_found() -> None:
    """Tests /run-test returns 404 when target file does not exist."""
    response = client.post(
        "/run-test", json={"test_file": "app/tests/test_nonexistent.py"}
    )
    assert response.status_code == 404
    assert "Test file not found" in response.json()["detail"]


@patch("app.main.Path.exists")
@patch("app.main.Path.is_file")
@patch("subprocess.run")
def test_run_test_pass(
    mock_run: MagicMock, mock_is_file: MagicMock, mock_exists: MagicMock
) -> None:
    """Tests /run-test when the test execution passes."""
    mock_exists.return_value = True
    mock_is_file.return_value = True

    mock_process = MagicMock(spec=subprocess.CompletedProcess)
    mock_process.returncode = 0
    mock_process.stdout = "All tests passed"
    mock_process.stderr = ""
    mock_run.return_value = mock_process

    response = client.post("/run-test", json={"test_file": "app/tests/test_main.py"})
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "pass"
    assert data["stdout"] == "All tests passed"
    assert data["duration_ms"] >= 0

    # Verify result is stored
    assert len(TEST_RESULTS) == 1
    assert TEST_RESULTS[0]["test_file"] == "app/tests/test_main.py"
    assert TEST_RESULTS[0]["status"] == "pass"


@patch("app.main.Path.exists")
@patch("app.main.Path.is_file")
@patch("subprocess.run")
def test_run_test_fail(
    mock_run: MagicMock, mock_is_file: MagicMock, mock_exists: MagicMock
) -> None:
    """Tests /run-test when the test execution fails."""
    mock_exists.return_value = True
    mock_is_file.return_value = True

    mock_process = MagicMock(spec=subprocess.CompletedProcess)
    mock_process.returncode = 1
    mock_process.stdout = "1 test failed"
    mock_process.stderr = "Error output"
    mock_run.return_value = mock_process

    response = client.post("/run-test", json={"test_file": "app/tests/test_main.py"})
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "fail"
    assert "1 test failed" in data["stdout"]
    assert "Error output" in data["stdout"]
    assert data["duration_ms"] >= 0

    # Verify result is stored
    assert len(TEST_RESULTS) == 1
    assert TEST_RESULTS[0]["status"] == "fail"


@patch("app.main.Path.exists")
@patch("app.main.Path.is_file")
@patch("subprocess.run")
def test_get_results_populated(
    mock_run: MagicMock, mock_is_file: MagicMock, mock_exists: MagicMock
) -> None:
    """Tests /results returns run histories after execution."""
    mock_exists.return_value = True
    mock_is_file.return_value = True

    mock_process = MagicMock(spec=subprocess.CompletedProcess)
    mock_process.returncode = 0
    mock_process.stdout = "Pass"
    mock_process.stderr = ""
    mock_run.return_value = mock_process

    # Execute a run
    client.post("/run-test", json={"test_file": "app/tests/test_main.py"})

    # Check results
    response = client.get("/results")
    assert response.status_code == 200
    results_list = response.json()
    assert len(results_list) == 1
    assert results_list[0]["test_file"] == "app/tests/test_main.py"
    assert results_list[0]["status"] == "pass"


@patch("app.main.Path.exists")
@patch("app.main.Path.is_file")
@patch("subprocess.run")
def test_run_test_subprocess_exception(
    mock_run: MagicMock, mock_is_file: MagicMock, mock_exists: MagicMock
) -> None:
    """Tests /run-test when subprocess raising an exception."""
    mock_exists.return_value = True
    mock_is_file.return_value = True
    mock_run.side_effect = RuntimeError("Subprocess crash")

    response = client.post("/run-test", json={"test_file": "app/tests/test_main.py"})
    assert response.status_code == 500
    assert "Subprocess execution failed" in response.json()["detail"]


def test_json_formatter_fields() -> None:
    """Tests that VerdictJsonFormatter correctly adds and structures fields."""
    formatter = VerdictJsonFormatter("%(asctime)s %(levelname)s %(name)s %(message)s")
    record = logging.LogRecord(
        name="test-logger",
        level=logging.INFO,
        pathname="test_file.py",
        lineno=10,
        msg="Test message",
        args=(),
        exc_info=None,
    )

    # Set request ID context
    token = request_id_var.set("test-request-id-123")
    try:
        formatted_str = formatter.format(record)
        formatted_json = json.loads(formatted_str)

        assert "timestamp" in formatted_json
        assert formatted_json["level"] == "INFO"
        assert formatted_json["service"] == "verdict-app"
        assert formatted_json["request_id"] == "test-request-id-123"
        assert formatted_json["message"] == "Test message"
    finally:
        request_id_var.reset(token)


def test_http_logging_format(caplog: pytest.LogCaptureFixture) -> None:
    """Verifies that HTTP requests produce log records with correct fields."""
    with caplog.at_level(logging.INFO):
        response = client.get("/health")
        assert response.status_code == 200

        # Find the request_completed log record
        request_completed_record = None
        for record in caplog.records:
            if record.message == "request_completed":
                request_completed_record = record
                break

        assert request_completed_record is not None, (
            f"Logs did not contain request_completed: {caplog.records}"
        )

        # Assert log record attributes
        assert request_completed_record.levelname == "INFO"
        assert getattr(request_completed_record, "path", None) == "/health"
        assert getattr(request_completed_record, "status", None) == 200
        assert hasattr(request_completed_record, "duration_ms")


@patch("boto3.client")
def test_load_application_secrets_success(mock_boto_client: MagicMock) -> None:
    """Tests load_application_secrets successfully fetches a secret."""
    mock_secrets_client = MagicMock()
    mock_secrets_client.get_secret_value.return_value = {
        "SecretString": '{"api_key": "some-val"}'
    }
    mock_boto_client.return_value = mock_secrets_client

    result = load_application_secrets(ignore_test_check=True)
    assert result == {"api_key": "some-val"}
    mock_boto_client.assert_called_once_with("secretsmanager", region_name="ap-south-1")
    mock_secrets_client.get_secret_value.assert_called_once_with(
        SecretId="verdict/app/api-key"
    )


@patch("boto3.client")
def test_load_application_secrets_failure(mock_boto_client: MagicMock) -> None:
    """Tests load_application_secrets error handling on failure."""
    mock_secrets_client = MagicMock()
    mock_secrets_client.get_secret_value.side_effect = RuntimeError(
        "AWS Connection Error"
    )
    mock_boto_client.return_value = mock_secrets_client

    result = load_application_secrets(ignore_test_check=True)
    assert result is None


def test_run_test_path_traversal() -> None:
    """Tests /run-test returns 400 when path traversal is attempted."""
    response = client.post("/run-test", json={"test_file": "../../../etc/passwd"})
    assert response.status_code == 400
    assert "Access denied: path traversal detected." in response.json()["detail"]
