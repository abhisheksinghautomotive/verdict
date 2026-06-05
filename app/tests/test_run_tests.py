"""Unit tests for run_tests.py script.

These tests cover argument parsing, JSON log formatting, subprocess handling
for port-forwarding, health checking, HTTP requests/responses, and main execution flows.
"""

import json
import logging
import subprocess
import sys
from pathlib import Path
from typing import Any, cast
from unittest.mock import MagicMock, patch

import pytest

# Add .github/scripts/ to sys.path programmatically
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / ".github" / "scripts"))

# pylint: disable=import-error,wrong-import-position
import run_tests


def test_json_formatter() -> None:
    """Tests that JsonFormatter produces valid JSON log records."""
    formatter = run_tests.JsonFormatter()
    log_record = logging.LogRecord(
        name="test-logger",
        level=logging.INFO,
        pathname="test.py",
        lineno=10,
        msg="test message %s",
        args=("here",),
        exc_info=None,
    )
    formatted = formatter.format(log_record)
    parsed = json.loads(formatted)

    assert parsed["level"] == "INFO"
    assert parsed["message"] == "test message here"
    assert parsed["name"] == "test-logger"
    assert "timestamp" in parsed


def test_parse_arguments() -> None:
    """Tests argument parsing returns expected test files and output path."""
    args = run_tests.parse_arguments(
        ["app/tests/test_main.py", "--output", "custom.json"]
    )
    assert args.test_files == ["app/tests/test_main.py"]
    assert args.output == "custom.json"


@patch("subprocess.Popen")
def test_start_port_forward(mock_popen: MagicMock) -> None:
    """Tests start_port_forward invokes kubectl port-forward correctly."""
    mock_process = MagicMock()
    mock_popen.return_value = mock_process

    proc = run_tests.start_port_forward()
    assert proc == mock_process
    mock_popen.assert_called_once_with(
        [
            "kubectl",
            "port-forward",
            "-n",
            "verdict",
            "svc/verdict-app",
            "8080:80",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
    )


@patch("urllib.request.urlopen")
def test_wait_for_health_check_success(mock_urlopen: MagicMock) -> None:
    """Tests wait_for_health_check returns True when endpoint is healthy."""
    mock_process = MagicMock()
    mock_process.poll.return_value = None

    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.read.return_value = b'{"status": "ok"}'
    mock_urlopen.return_value.__enter__.return_value = mock_response

    res = run_tests.wait_for_health_check(mock_process, timeout=1.0)
    assert res is True


@patch("urllib.request.urlopen")
@patch("time.sleep")
def test_wait_for_health_check_timeout(
    mock_sleep: MagicMock, mock_urlopen: MagicMock
) -> None:
    """Tests wait_for_health_check returns False when endpoint times out."""
    mock_process = MagicMock()
    mock_process.poll.return_value = None
    mock_urlopen.side_effect = Exception("Connection refused")

    res = run_tests.wait_for_health_check(mock_process, timeout=0.1)
    assert res is False


@patch("urllib.request.urlopen")
def test_wait_for_health_check_early_exit(mock_urlopen: MagicMock) -> None:
    """Tests wait_for_health_check returns False if port-forward exits early."""
    mock_process = MagicMock()
    mock_process.poll.return_value = 1
    mock_process.stderr = MagicMock()
    mock_process.stderr.read.return_value = "Port 8080 already in use"

    res = run_tests.wait_for_health_check(mock_process, timeout=1.0)
    assert res is False


@patch("urllib.request.urlopen")
def test_run_test_file_success(mock_urlopen: MagicMock) -> None:
    """Tests run_test_file processes successful test execution response."""
    mock_response = MagicMock()
    mock_response.read.return_value = (
        b'{"status": "pass", "stdout": "All passed", "duration_ms": 120}'
    )
    mock_urlopen.return_value.__enter__.return_value = mock_response

    res = run_tests.run_test_file("app/tests/test_main.py")
    assert res["status"] == "pass"
    assert res["stdout"] == "All passed"
    assert res["duration_ms"] == 120


@patch("urllib.request.urlopen")
def test_run_test_file_http_error(mock_urlopen: MagicMock) -> None:
    """Tests run_test_file handles HTTPError responses gracefully."""
    from urllib.error import HTTPError

    mock_err_response = MagicMock()
    mock_err_response.read.return_value = b"Not Found"

    err = HTTPError(
        "http://localhost:8080/run-test",
        404,
        "Not Found",
        cast(Any, {}),
        mock_err_response,
    )
    mock_urlopen.side_effect = err

    res = run_tests.run_test_file("app/tests/test_main.py")
    assert res["status"] == "fail"
    assert "HTTP Error 404" in res["stdout"]
    assert "Not Found" in res["stdout"]


@patch("urllib.request.urlopen")
def test_run_test_file_http_error_read_fail(mock_urlopen: MagicMock) -> None:
    """Tests run_test_file handles HTTPError with unreadable response body."""
    from urllib.error import HTTPError

    mock_err_response = MagicMock()
    mock_err_response.read.side_effect = Exception("Read failed")

    err = HTTPError(
        "http://localhost:8080/run-test",
        404,
        "Not Found",
        cast(Any, {}),
        mock_err_response,
    )
    mock_urlopen.side_effect = err

    res = run_tests.run_test_file("app/tests/test_main.py")
    assert res["status"] == "fail"
    assert "HTTP Error 404" in res["stdout"]


@patch("urllib.request.urlopen")
def test_run_test_file_exception(mock_urlopen: MagicMock) -> None:
    """Tests run_test_file handles generic exceptions during HTTP calls."""
    mock_urlopen.side_effect = RuntimeError("Socket timeout")

    res = run_tests.run_test_file("app/tests/test_main.py")
    assert res["status"] == "fail"
    assert "Unexpected execution error" in res["stdout"]


def test_write_results_file(tmp_path: Path) -> None:
    """Tests write_results_file writes results dict to output path as JSON."""
    out_file = tmp_path / "results.json"
    results = [
        {
            "test_file": "app/tests/test_main.py",
            "status": "pass",
            "stdout": "ok",
            "duration_ms": 100,
        }
    ]
    run_tests.write_results_file(out_file, results)

    assert out_file.exists()
    with open(out_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert data == results


@patch("run_tests.start_port_forward")
@patch("run_tests.wait_for_health_check")
@patch("run_tests.run_test_file")
@patch("run_tests.write_results_file")
def test_main_success(
    mock_write: MagicMock,
    mock_run: MagicMock,
    mock_wait: MagicMock,
    mock_forward: MagicMock,
) -> None:
    """Tests main function exits with 0 on successful test runs."""
    mock_proc = MagicMock()
    mock_forward.return_value = mock_proc
    mock_wait.return_value = True

    mock_run.return_value = {
        "status": "pass",
        "stdout": "ok",
        "duration_ms": 100,
    }

    with pytest.raises(SystemExit) as exc_info:
        run_tests.main(["app/tests/test_main.py", "--output", "results.json"])

    assert exc_info.value.code == 0
    mock_proc.terminate.assert_called_once()
    mock_write.assert_called_once()


@patch("run_tests.start_port_forward")
@patch("run_tests.wait_for_health_check")
@patch("run_tests.run_test_file")
@patch("run_tests.write_results_file")
def test_main_test_failure(
    mock_write: MagicMock,
    mock_run: MagicMock,
    mock_wait: MagicMock,
    mock_forward: MagicMock,
) -> None:
    """Tests main function exits with 1 when some tests fail."""
    mock_proc = MagicMock()
    mock_forward.return_value = mock_proc
    mock_wait.return_value = True

    mock_run.return_value = {
        "status": "fail",
        "stdout": "failed",
        "duration_ms": 100,
    }

    with pytest.raises(SystemExit) as exc_info:
        run_tests.main(["app/tests/test_main.py"])

    assert exc_info.value.code == 1
    mock_proc.terminate.assert_called_once()
    mock_write.assert_called_once()


@patch("run_tests.start_port_forward")
@patch("run_tests.wait_for_health_check")
def test_main_health_check_failure(
    mock_wait: MagicMock,
    mock_forward: MagicMock,
) -> None:
    """Tests main function exits with 1 when health checks fail."""
    mock_proc = MagicMock()
    mock_forward.return_value = mock_proc
    mock_wait.return_value = False

    with pytest.raises(SystemExit) as exc_info:
        run_tests.main(["app/tests/test_main.py"])

    assert exc_info.value.code == 1
    mock_proc.terminate.assert_called_once()
