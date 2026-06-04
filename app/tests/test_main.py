import subprocess
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import TEST_RESULTS, app

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
    response = client.post("/run-test", json={"test_file": "nonexistent_file.py"})
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
