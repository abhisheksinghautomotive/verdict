"""Unit tests for detect_changed_tests.py script.

These tests cover argument parsing, git diff execution, GitHub Actions output
writing, and correct filtering of test files.
"""

import json
import logging
import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Add .github/scripts/ to sys.path programmatically
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / ".github" / "scripts"))

# pylint: disable=import-error,wrong-import-position
import detect_changed_tests


def test_json_formatter() -> None:
    """Tests that JsonFormatter produces valid JSON log records."""
    formatter = detect_changed_tests.JsonFormatter()
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


@patch("subprocess.run")
def test_run_git_diff_success(mock_run: MagicMock) -> None:
    """Tests run_git_diff returns correct list of files when successful."""
    mock_process = MagicMock(spec=subprocess.CompletedProcess)
    mock_process.stdout = "file1.txt\napp/tests/test_main.py\n\n"
    mock_process.returncode = 0
    mock_run.return_value = mock_process

    result = detect_changed_tests.run_git_diff("main", "HEAD")
    assert result == ["file1.txt", "app/tests/test_main.py"]
    mock_run.assert_called_once_with(
        ["git", "diff", "--name-only", "main...HEAD"],
        capture_output=True,
        text=True,
        check=True,
    )


@patch("subprocess.run")
def test_run_git_diff_failure(mock_run: MagicMock) -> None:
    """Tests run_git_diff raises RuntimeError on command failure."""
    mock_run.side_effect = subprocess.CalledProcessError(
        returncode=128,
        cmd=["git", "diff"],
        stderr="fatal: Not a valid object name main",
    )

    with pytest.raises(RuntimeError) as exc_info:
        detect_changed_tests.run_git_diff("main", "HEAD")

    assert "Git diff failed" in str(exc_info.value)


def test_write_github_output(tmp_path: Path) -> None:
    """Tests write_github_output writes key-value pairs correctly."""
    output_file = tmp_path / "github_output"
    detect_changed_tests.write_github_output(str(output_file), "key1", "val1")
    detect_changed_tests.write_github_output(str(output_file), "key2", "val2")

    content = output_file.read_text(encoding="utf-8")
    assert content == "key1=val1\nkey2=val2\n"


def test_parse_arguments() -> None:
    """Tests argument parsing returns expected base and head values."""
    args = detect_changed_tests.parse_arguments(["--base", "main", "--head", "HEAD"])
    assert args.base == "main"
    assert args.head == "HEAD"


@patch("detect_changed_tests.run_git_diff")
def test_main_no_github_output(
    mock_diff: MagicMock, caplog: pytest.LogCaptureFixture
) -> None:
    """Tests main function when GITHUB_OUTPUT environment variable is not set."""
    mock_diff.return_value = ["app/tests/test_main.py", "app/main.py"]

    with patch.dict("os.environ", {}, clear=True):
        with caplog.at_level(logging.INFO):
            detect_changed_tests.main(["--base", "main", "--head", "HEAD"])

    assert "Detected changed tests: ['app/tests/test_main.py']" in caplog.text
    assert "GITHUB_OUTPUT is not set" in caplog.text


@patch("detect_changed_tests.run_git_diff")
def test_main_with_github_output(
    mock_diff: MagicMock, tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """Tests main function writes to GITHUB_OUTPUT when the variable is set."""
    mock_diff.return_value = [
        "app/tests/test_main.py",
        "app/main.py",
        "app/tests/test_other.py",
        "app/tests/test_detect_changed_tests.py",
        "app/tests/test_run_tests.py",
    ]
    output_file = tmp_path / "output.txt"

    with patch.dict("os.environ", {"GITHUB_OUTPUT": str(output_file)}):
        with caplog.at_level(logging.INFO):
            detect_changed_tests.main(["--base", "main", "--head", "HEAD"])

    assert "GITHUB_OUTPUT is set" in caplog.text

    content = output_file.read_text(encoding="utf-8")
    assert "changed_tests=app/tests/test_main.py app/tests/test_other.py\n" in content
    assert (
        'changed_tests_json=["app/tests/test_main.py", "app/tests/test_other.py"]\n'
        in content
    )
    assert "has_changed_tests=true\n" in content


@patch("detect_changed_tests.run_git_diff")
def test_main_git_diff_failure_exits(mock_diff: MagicMock) -> None:
    """Tests main function exits with status 1 if git diff fails."""
    mock_diff.side_effect = RuntimeError("Git diff failed")

    with pytest.raises(SystemExit) as exc_info:
        detect_changed_tests.main(["--base", "main", "--head", "HEAD"])

    assert exc_info.value.code == 1


@patch("detect_changed_tests.run_git_diff")
def test_main_write_failure_exits(mock_diff: MagicMock, tmp_path: Path) -> None:
    """Tests main function exits with status 1 if GITHUB_OUTPUT write fails."""
    mock_diff.return_value = ["app/tests/test_main.py"]
    # Provide a directory path so that writing to it fails with IsADirectoryError / IOError
    invalid_file = tmp_path / "dir_instead_of_file"
    invalid_file.mkdir()

    with patch.dict("os.environ", {"GITHUB_OUTPUT": str(invalid_file)}):
        with pytest.raises(SystemExit) as exc_info:
            detect_changed_tests.main(["--base", "main", "--head", "HEAD"])

    assert exc_info.value.code == 1
