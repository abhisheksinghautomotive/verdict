"""Unit tests for post_tf_plan.py script.

These tests cover parsing GitHub event payloads, parsing Terraform plan files,
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
import post_tf_plan


def test_json_formatter() -> None:
    """Tests that JsonFormatter produces valid JSON log records."""
    formatter = post_tf_plan.JsonFormatter()
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
    assert post_tf_plan.get_pr_number(None) is None
    assert post_tf_plan.get_pr_number("nonexistent_file.json") is None


def test_get_pr_number_from_pull_request_event(tmp_path: Path) -> None:
    """Tests get_pr_number parses PR number from standard pull_request event payload."""
    event_file = tmp_path / "event.json"
    payload = {"pull_request": {"number": 42}}
    with open(event_file, "w", encoding="utf-8") as f:
        json.dump(payload, f)

    assert post_tf_plan.get_pr_number(str(event_file)) == 42


def test_get_pr_number_from_fallback(tmp_path: Path) -> None:
    """Tests get_pr_number parses number from fallback payload field."""
    event_file = tmp_path / "event.json"
    payload = {"number": 101}
    with open(event_file, "w", encoding="utf-8") as f:
        json.dump(payload, f)

    assert post_tf_plan.get_pr_number(str(event_file)) == 101


def test_get_pr_number_parse_exception(tmp_path: Path) -> None:
    """Tests get_pr_number returns None on malformed JSON payload."""
    event_file = tmp_path / "event.json"
    with open(event_file, "w", encoding="utf-8") as f:
        f.write("invalid json")

    assert post_tf_plan.get_pr_number(str(event_file)) is None


def test_parse_plan_file_missing_or_invalid(tmp_path: Path) -> None:
    """Tests parse_plan_file handles missing or malformed plan files."""
    assert post_tf_plan.parse_plan_file(Path("nonexistent.txt")) == (0, 0, 0, "")


def test_parse_plan_file_read_error(tmp_path: Path) -> None:
    """Tests parse_plan_file returns empty tuple on file read errors."""
    unreadable_file = tmp_path / "unreadable.txt"
    unreadable_file.touch()

    with patch.object(
        Path, "read_text", side_effect=PermissionError("Permission denied")
    ):
        added, changed, destroyed, content = post_tf_plan.parse_plan_file(
            unreadable_file
        )
        assert added == 0
        assert changed == 0
        assert destroyed == 0
        assert content == ""


def test_parse_plan_file_no_changes(tmp_path: Path) -> None:
    """Tests parse_plan_file parses plan with no changes correctly."""
    valid_file = tmp_path / "plan.txt"
    content = "No changes. Your infrastructure matches the configuration."
    valid_file.write_text(content, encoding="utf-8")

    added, changed, destroyed, plan_content = post_tf_plan.parse_plan_file(valid_file)
    assert added == 0
    assert changed == 0
    assert destroyed == 0
    assert plan_content == content


def test_parse_plan_file_with_changes(tmp_path: Path) -> None:
    """Tests parse_plan_file parses plan with additions/changes/destructions correctly."""
    valid_file = tmp_path / "plan.txt"
    content = """
Terraform will perform the following actions:
# aws_security_group.eks_nodes will be created
+ sg-12345
Plan: 3 to add, 1 to change, 2 to destroy.
"""
    valid_file.write_text(content, encoding="utf-8")

    added, changed, destroyed, plan_content = post_tf_plan.parse_plan_file(valid_file)
    assert added == 3
    assert changed == 1
    assert destroyed == 2
    assert plan_content == content


def test_generate_comment_body_empty() -> None:
    """Tests comment generation for empty or missing plan content."""
    body = post_tf_plan.generate_comment_body(
        added=0,
        changed=0,
        destroyed=0,
        plan_content="",
        repo="owner/repo",
        run_id="123",
        server_url="https://github.com",
    )
    assert post_tf_plan.MARKER in body
    assert "🔴 PLAN FAILURE" in body


def test_generate_comment_body_no_changes() -> None:
    """Tests comment generation when plan has no changes."""
    body = post_tf_plan.generate_comment_body(
        added=0,
        changed=0,
        destroyed=0,
        plan_content="No changes. Your infrastructure matches the configuration.",
        repo="owner/repo",
        run_id="123",
        server_url="https://github.com",
    )
    assert post_tf_plan.MARKER in body
    assert "🟢 NO CHANGES" in body
    assert "Add** | 0" in body
    assert "Change** | 0" in body
    assert "Destroy** | 0" in body


def test_generate_comment_body_with_changes() -> None:
    """Tests comment generation when plan has planned changes."""
    body = post_tf_plan.generate_comment_body(
        added=5,
        changed=2,
        destroyed=1,
        plan_content="Plan: 5 to add, 2 to change, 1 to destroy.",
        repo="owner/repo",
        run_id="123",
        server_url="https://github.com",
    )
    assert post_tf_plan.MARKER in body
    assert "🟡 CHANGES PLANNED" in body
    assert "Add** | 5" in body
    assert "Change** | 2" in body
    assert "Destroy** | 1" in body


def test_generate_comment_body_truncation() -> None:
    """Tests comment generation truncates extremely long plan output."""
    long_content = "X" * 70000
    body = post_tf_plan.generate_comment_body(
        added=1,
        changed=0,
        destroyed=0,
        plan_content=long_content,
        repo="owner/repo",
        run_id="123",
        server_url="https://github.com",
    )
    assert "Plan output truncated" in body
    assert len(body) < 70000


@patch("urllib.request.urlopen")
def test_github_request_success(mock_urlopen: MagicMock) -> None:
    """Tests github_request returns parsed JSON response on success."""
    mock_response = MagicMock()
    mock_response.read.return_value = b'{"id": 456, "body": "hello"}'
    mock_urlopen.return_value.__enter__.return_value = mock_response

    res = post_tf_plan.github_request("https://api.github.com/test", "token", "GET")
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
        post_tf_plan.github_request("https://api.github.com/test", "token", "GET")


@patch("post_tf_plan.github_request")
def test_find_existing_comment_found(mock_request: MagicMock) -> None:
    """Tests find_existing_comment returns comment ID when comment with marker is found."""
    mock_request.return_value = [
        {"id": 11, "body": "other comment"},
        {"id": 12, "body": f"some text\n{post_tf_plan.MARKER}\nmore text"},
    ]
    res = post_tf_plan.find_existing_comment(
        "https://api.github.com", "owner/repo", 42, "token"
    )
    assert res == 12


@patch("post_tf_plan.github_request")
def test_find_existing_comment_not_found(mock_request: MagicMock) -> None:
    """Tests find_existing_comment returns None when no comment with marker exists."""
    mock_request.return_value = [
        {"id": 11, "body": "other comment"},
    ]
    res = post_tf_plan.find_existing_comment(
        "https://api.github.com", "owner/repo", 42, "token"
    )
    assert res is None


@patch("post_tf_plan.github_request")
def test_find_existing_comment_error(mock_request: MagicMock) -> None:
    """Tests find_existing_comment returns None when the request fails."""
    mock_request.side_effect = Exception("API error")
    res = post_tf_plan.find_existing_comment(
        "https://api.github.com", "owner/repo", 42, "token"
    )
    assert res is None


@patch("post_tf_plan.find_existing_comment")
@patch("post_tf_plan.github_request")
def test_upsert_comment_create(mock_request: MagicMock, mock_find: MagicMock) -> None:
    """Tests upsert_comment performs POST when no comment is found."""
    mock_find.return_value = None

    post_tf_plan.upsert_comment(
        "https://api.github.com", "owner/repo", 42, "token", "new body"
    )

    mock_request.assert_called_once_with(
        "https://api.github.com/repos/owner/repo/issues/42/comments",
        "token",
        "POST",
        {"body": "new body"},
    )


@patch("post_tf_plan.find_existing_comment")
@patch("post_tf_plan.github_request")
def test_upsert_comment_update(mock_request: MagicMock, mock_find: MagicMock) -> None:
    """Tests upsert_comment performs PATCH when an existing comment is found."""
    mock_find.return_value = 12

    post_tf_plan.upsert_comment(
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
    args = post_tf_plan.parse_arguments(["--plan-file", "p.txt", "--pr-number", "55"])
    assert args.plan_file == "p.txt"
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
@patch("post_tf_plan.get_pr_number")
@patch("post_tf_plan.parse_plan_file")
@patch("post_tf_plan.upsert_comment")
def test_main_success(
    mock_upsert: MagicMock, mock_parse: MagicMock, mock_pr: MagicMock
) -> None:
    """Tests main execution success path when all environment inputs are set."""
    mock_pr.return_value = 42
    mock_parse.return_value = (1, 2, 3, "Plan details")

    post_tf_plan.main(["--plan-file", "plan.txt"])

    mock_upsert.assert_called_once()
    assert "🟡 CHANGES PLANNED" in mock_upsert.call_args.kwargs["body"]


@patch.dict(os.environ, {}, clear=True)
def test_main_missing_env() -> None:
    """Tests main exits with 1 when essential environment variables are missing."""
    with pytest.raises(SystemExit) as exc_info:
        post_tf_plan.main(["--plan-file", "plan.txt"])
    assert exc_info.value.code == 1
