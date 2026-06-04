"""Unit tests for post_pr_comment.py script.

These tests cover parsing GitHub event payloads, parsing test results files,
formatting the Markdown comment body, sending requests to the GitHub API,
and verifying the main script execution flow under different environment conditions.
"""

import json
import logging
import os
import sys
from pathlib import Path
from typing import Any, cast
from unittest.mock import MagicMock, patch

import pytest

# Add .github/scripts/ to sys.path programmatically
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / ".github" / "scripts"))

# pylint: disable=import-error,wrong-import-position
import post_pr_comment


def test_json_formatter() -> None:
    """Tests that JsonFormatter produces valid JSON log records."""
    formatter = post_pr_comment.JsonFormatter()
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


def test_get_pr_number_missing_or_invalid() -> None:
    """Tests get_pr_number returns None on missing or invalid event path."""
    assert post_pr_comment.get_pr_number(None) is None
    assert post_pr_comment.get_pr_number("nonexistent_file.json") is None


def test_get_pr_number_from_pull_request_event(tmp_path: Path) -> None:
    """Tests get_pr_number parses PR number from standard pull_request event payload."""
    event_file = tmp_path / "event.json"
    payload = {"pull_request": {"number": 42}}
    with open(event_file, "w", encoding="utf-8") as f:
        json.dump(payload, f)

    assert post_pr_comment.get_pr_number(str(event_file)) == 42


def test_get_pr_number_from_fallback(tmp_path: Path) -> None:
    """Tests get_pr_number parses number from fallback payload field."""
    event_file = tmp_path / "event.json"
    payload = {"number": 101}
    with open(event_file, "w", encoding="utf-8") as f:
        json.dump(payload, f)

    assert post_pr_comment.get_pr_number(str(event_file)) == 101


def test_get_pr_number_parse_exception(tmp_path: Path) -> None:
    """Tests get_pr_number returns None on malformed JSON payload."""
    event_file = tmp_path / "event.json"
    with open(event_file, "w", encoding="utf-8") as f:
        f.write("invalid json")

    assert post_pr_comment.get_pr_number(str(event_file)) is None


def test_parse_results_missing_or_invalid(tmp_path: Path) -> None:
    """Tests parse_results handles missing or malformed results files."""
    assert post_pr_comment.parse_results(Path("nonexistent.json")) == []

    invalid_file = tmp_path / "invalid.json"
    with open(invalid_file, "w", encoding="utf-8") as f:
        f.write("invalid json")
    assert post_pr_comment.parse_results(invalid_file) == []

    not_list_file = tmp_path / "dict.json"
    with open(not_list_file, "w", encoding="utf-8") as f:
        json.dump({"status": "pass"}, f)
    assert post_pr_comment.parse_results(not_list_file) == []


def test_parse_results_valid(tmp_path: Path) -> None:
    """Tests parse_results parses a valid list of results correctly."""
    valid_file = tmp_path / "results.json"
    results = [
        {"test_file": "app/tests/test_main.py", "status": "pass", "duration_ms": 10}
    ]
    with open(valid_file, "w", encoding="utf-8") as f:
        json.dump(results, f)

    assert post_pr_comment.parse_results(valid_file) == results


def test_generate_comment_body_empty_success() -> None:
    """Tests comment generation for empty results when job status is success."""
    body = post_pr_comment.generate_comment_body(
        results=[],
        job_status="success",
        repo="owner/repo",
        run_id="123",
        server_url="https://github.com",
    )
    assert post_pr_comment.MARKER in body
    assert "🟡 NO TESTS RUN" in body
    assert "actions/runs/123" in body


def test_generate_comment_body_empty_failure() -> None:
    """Tests comment generation for empty results when job status is failure."""
    body = post_pr_comment.generate_comment_body(
        results=[],
        job_status="failure",
        repo="owner/repo",
        run_id="123",
        server_url="https://github.com",
    )
    assert post_pr_comment.MARKER in body
    assert "🔴 SETUP FAILURE" in body
    assert "actions/runs/123" in body


def test_generate_comment_body_all_pass() -> None:
    """Tests comment generation when all tests pass."""
    results = [
        {"test_file": "app/tests/test_main.py", "status": "pass", "duration_ms": 50}
    ]
    body = post_pr_comment.generate_comment_body(
        results=results,
        job_status="success",
        repo="owner/repo",
        run_id="123",
        server_url="https://github.com",
    )
    assert post_pr_comment.MARKER in body
    assert "🟢 PASS" in body
    assert "Total Test Files** | 1" in body
    assert "Passed** | 1" in body
    assert "Failed** | 0" in body
    assert "Failing Test Files" not in body


def test_generate_comment_body_some_fail() -> None:
    """Tests comment generation when some tests fail."""
    results = [
        {"test_file": "app/tests/test_main.py", "status": "pass", "duration_ms": 50},
        {
            "test_file": "app/tests/test_fail.py",
            "status": "fail",
            "duration_ms": 120,
            "stdout": "AssertionError",
        },
    ]
    body = post_pr_comment.generate_comment_body(
        results=results,
        job_status="failure",
        repo="owner/repo",
        run_id="123",
        server_url="https://github.com",
    )
    assert post_pr_comment.MARKER in body
    assert "🔴 FAIL" in body
    assert "Total Test Files** | 2" in body
    assert "Passed** | 1" in body
    assert "Failed** | 1" in body
    assert "Failing Test Files" in body
    assert "`app/tests/test_fail.py` | `fail` | 120ms" in body
    assert "AssertionError" in body


@patch("urllib.request.urlopen")
def test_github_request_success(mock_urlopen: MagicMock) -> None:
    """Tests github_request returns parsed JSON response on success."""
    mock_response = MagicMock()
    mock_response.read.return_value = b'{"id": 456, "body": "hello"}'
    mock_urlopen.return_value.__enter__.return_value = mock_response

    res = post_pr_comment.github_request("https://api.github.com/test", "token", "GET")
    assert res == {"id": 456, "body": "hello"}


@patch("urllib.request.urlopen")
def test_github_request_http_error(mock_urlopen: MagicMock) -> None:
    """Tests github_request raises HTTPError on API failures."""
    from urllib.error import HTTPError

    mock_err_response = MagicMock()
    mock_err_response.read.return_value = b"Forbidden"

    err = HTTPError(
        "https://api.github.com/test",
        403,
        "Forbidden",
        cast(Any, {}),
        mock_err_response,
    )
    mock_urlopen.side_effect = err

    with pytest.raises(HTTPError):
        post_pr_comment.github_request("https://api.github.com/test", "token", "GET")


@patch("post_pr_comment.github_request")
def test_find_existing_comment_found(mock_request: MagicMock) -> None:
    """Tests find_existing_comment returns comment ID when comment with marker is found."""
    mock_request.return_value = [
        {"id": 11, "body": "other comment"},
        {"id": 12, "body": f"some text\n{post_pr_comment.MARKER}\nmore text"},
    ]
    res = post_pr_comment.find_existing_comment(
        "https://api.github.com", "owner/repo", 42, "token"
    )
    assert res == 12


@patch("post_pr_comment.github_request")
def test_find_existing_comment_not_found(mock_request: MagicMock) -> None:
    """Tests find_existing_comment returns None when no comment with marker exists."""
    mock_request.return_value = [
        {"id": 11, "body": "other comment"},
    ]
    res = post_pr_comment.find_existing_comment(
        "https://api.github.com", "owner/repo", 42, "token"
    )
    assert res is None


@patch("post_pr_comment.github_request")
def test_find_existing_comment_error(mock_request: MagicMock) -> None:
    """Tests find_existing_comment returns None when the request fails."""
    mock_request.side_effect = Exception("API error")
    res = post_pr_comment.find_existing_comment(
        "https://api.github.com", "owner/repo", 42, "token"
    )
    assert res is None


@patch("post_pr_comment.find_existing_comment")
@patch("post_pr_comment.github_request")
def test_upsert_comment_create(mock_request: MagicMock, mock_find: MagicMock) -> None:
    """Tests upsert_comment performs POST when no comment is found."""
    mock_find.return_value = None

    post_pr_comment.upsert_comment(
        "https://api.github.com", "owner/repo", 42, "token", "new body"
    )

    mock_request.assert_called_once_with(
        "https://api.github.com/repos/owner/repo/issues/42/comments",
        "token",
        "POST",
        {"body": "new body"},
    )


@patch("post_pr_comment.find_existing_comment")
@patch("post_pr_comment.github_request")
def test_upsert_comment_update(mock_request: MagicMock, mock_find: MagicMock) -> None:
    """Tests upsert_comment performs PATCH when an existing comment is found."""
    mock_find.return_value = 12

    post_pr_comment.upsert_comment(
        "https://api.github.com", "owner/repo", 42, "token", "updated body"
    )

    mock_request.assert_called_once_with(
        "https://api.github.com/repos/owner/repo/issues/comments/12",
        "token",
        "PATCH",
        {"body": "updated body"},
    )


def test_parse_arguments() -> None:
    """Tests that argument parsing resolves parameters correctly."""
    args = post_pr_comment.parse_arguments(
        ["--results-file", "r.json", "--status", "failure", "--pr-number", "55"]
    )
    assert args.results_file == "r.json"
    assert args.status == "failure"
    assert args.pr_number == 55


@patch.dict(
    os.environ,
    {
        "GITHUB_TOKEN": "mock-token",
        "GITHUB_REPOSITORY": "owner/repo",
        "GITHUB_RUN_ID": "999",
        "GITHUB_EVENT_PATH": "/mock/event.json",
    },
)
@patch("post_pr_comment.get_pr_number")
@patch("post_pr_comment.parse_results")
@patch("post_pr_comment.upsert_comment")
def test_main_success(
    mock_upsert: MagicMock, mock_parse: MagicMock, mock_pr: MagicMock
) -> None:
    """Tests main execution success path when all environment inputs are set."""
    mock_pr.return_value = 42
    mock_parse.return_value = [{"status": "pass", "test_file": "test.py"}]

    post_pr_comment.main([])

    mock_upsert.assert_called_once()
    assert "🟢 PASS" in mock_upsert.call_args.kwargs["body"]


@patch.dict(os.environ, {}, clear=True)
def test_main_missing_env() -> None:
    """Tests main exits with 1 when essential environment variables are missing."""
    with pytest.raises(SystemExit) as exc_info:
        post_pr_comment.main([])
    assert exc_info.value.code == 1
