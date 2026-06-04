#!/usr/bin/env python3
"""Post test execution results as a sticky comment on a GitHub PR."""

import argparse
import json
import logging
import os
import sys
import urllib.request
import urllib.error
from pathlib import Path
from typing import Any, Sequence

MARKER = "<!-- verdict-test-gate -->"


class JsonFormatter(logging.Formatter):
    """Custom formatter to format log records as JSON."""

    def format(self, record: logging.LogRecord) -> str:
        """Formats the log record as a JSON string.

        Args:
            record: The log record to format.

        Returns:
            str: The JSON formatted log line.
        """
        log_record = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "message": record.getMessage(),
            "name": record.name,
        }
        if record.exc_info:
            log_record["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(log_record)


# Configure logging using our custom JSON Formatter
logger = logging.getLogger("post-pr-comment")
handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(JsonFormatter())
logger.addHandler(handler)
logger.setLevel(logging.INFO)


def get_pr_number(event_path: str | None) -> int | None:
    """Extract the pull request number from the GitHub event payload.

    Args:
        event_path: Path to the GITHUB_EVENT_PATH JSON file.

    Returns:
        int | None: The PR number if found, otherwise None.
    """
    if not event_path:
        return None
    try:
        path = Path(event_path)
        if not path.exists():
            logger.warning("Event path file does not exist: %s", event_path)
            return None
        with open(path, "r", encoding="utf-8") as f:
            event_data = json.load(f)
        # Check standard pull_request payload
        pr_data = event_data.get("pull_request")
        if isinstance(pr_data, dict):
            num = pr_data.get("number")
            if num is not None:
                return int(num)
        # Fallback for issue comment or raw issue fields
        num = event_data.get("number")
        if num is not None:
            return int(num)
    except Exception as exc:
        logger.warning("Failed to parse event payload: %s", exc)
    return None


def parse_results(results_path: Path) -> list[dict[str, Any]]:
    """Parse the test results JSON file.

    Args:
        results_path: Path to the test_results.json file.

    Returns:
        list[dict[str, Any]]: Parsed test results.
    """
    if not results_path.exists():
        logger.warning("Test results file not found at %s", results_path)
        return []
    try:
        with open(results_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                return data
            logger.warning("Test results JSON is not a list")
    except Exception as exc:
        logger.error("Failed to parse test results JSON: %s", exc)
    return []


def generate_comment_body(
    results: list[dict[str, Any]],
    job_status: str,
    repo: str,
    run_id: str,
    server_url: str,
) -> str:
    """Generate the markdown comment body summarizing the results.

    Args:
        results: List of test results.
        job_status: The GHA job status ('success', 'failure', etc.).
        repo: The repository name (e.g. owner/repo).
        run_id: The GHA run ID.
        server_url: The GitHub server URL.

    Returns:
        str: Markdown formatted comment body.
    """
    run_url = f"{server_url}/{repo}/actions/runs/{run_id}"

    if not results:
        # Check if the overall job failed or was cancelled
        if job_status != "success":
            verdict_status = "🔴 SETUP FAILURE"
            details_text = (
                "The test gate workflow failed during build, deployment, or setup."
            )
        else:
            verdict_status = "🟡 NO TESTS RUN"
            details_text = (
                "No test results were found, but the workflow finished successfully."
            )

        return f"""{MARKER}
## Verdict Test Gate Results

| Metric | Value |
| :--- | :--- |
| **Verdict** | **{verdict_status}** |
| **Details** | {details_text} |
| **Workflow Run** | [Run #{run_id}]({run_url}) |
"""

    total = len(results)
    passed = sum(1 for r in results if r.get("status") == "pass")
    failed = total - passed

    if failed > 0:
        verdict_status = "🔴 FAIL"
        verdict_emoji = "🔴"
    else:
        verdict_status = "🟢 PASS"
        verdict_emoji = "🟢"

    body = f"""{MARKER}
## Verdict Test Gate Results

| Metric | Value |
| :--- | :--- |
| **Verdict** | {verdict_emoji} **{verdict_status}** |
| **Total Test Files** | {total} |
| **Passed** | {passed} |
| **Failed** | {failed} |
| **Workflow Run** | [Run #{run_id}]({run_url}) |
"""

    # Add failing files section
    if failed > 0:
        body += "\n### 🔴 Failing Test Files\n\n"
        body += "| File | Status | Duration |\n"
        body += "| :--- | :--- | :--- |\n"
        for r in results:
            if r.get("status") != "pass":
                file = r.get("test_file", "unknown")
                status = r.get("status", "fail")
                duration = f"{r.get('duration_ms', 0)}ms"
                body += f"| `{file}` | `{status}` | {duration} |\n"

        # Add failed logs detail drop-downs
        body += "\n### 🔍 Execution Logs for Failed Tests\n"
        for r in results:
            if r.get("status") != "pass":
                file = r.get("test_file", "unknown")
                stdout = r.get("stdout", "No stdout captured.")
                body += f"\n<details>\n<summary><b>Logs: {file}</b></summary>\n\n"
                body += "```\n"
                body += stdout
                body += "\n```\n"
                body += "</details>\n"

    return body


def github_request(
    url: str, token: str, method: str, data: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Helper function to make requests to the GitHub API.

    Args:
        url: The API endpoint URL.
        token: GITHUB_TOKEN for authorization.
        method: HTTP method (GET, POST, PATCH, etc.).
        data: Optional dict to be sent as JSON body.

    Returns:
        dict[str, Any]: Parsed JSON response.
    """
    req = urllib.request.Request(url, method=method)
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Accept", "application/vnd.github.v3+json")
    req.add_header("User-Agent", "verdict-gha")

    req_data = None
    if data is not None:
        req_data = json.dumps(data).encode("utf-8")
        req.add_header("Content-Type", "application/json")

    try:
        with urllib.request.urlopen(req, data=req_data, timeout=30.0) as response:
            res_body = response.read().decode("utf-8")
            if res_body:
                res_json: dict[str, Any] = json.loads(res_body)
                return res_json
            return {}
    except urllib.error.HTTPError as err:
        error_body = ""
        try:
            error_body = err.read().decode("utf-8")
        except Exception:
            pass
        logger.error(
            "GitHub API request failed: %s %s. Code: %d, Response: %s",
            method,
            url,
            err.code,
            error_body,
        )
        raise
    except Exception as exc:
        logger.error("GitHub API request encountered an error: %s", exc)
        raise


def find_existing_comment(
    api_url: str, repo: str, pr_number: int, token: str
) -> int | None:
    """Find an existing comment containing the marker.

    Args:
        api_url: GitHub API URL.
        repo: Repository owner/name.
        pr_number: Pull request number.
        token: GitHub Token.

    Returns:
        int | None: The comment ID if found, otherwise None.
    """
    url = f"{api_url}/repos/{repo}/issues/{pr_number}/comments"
    logger.info("Fetching comments from %s", url)
    try:
        # Fetching comments (up to 100 for simplicity)
        comments = github_request(f"{url}?per_page=100", token, "GET")
        if isinstance(comments, list):
            for comment in comments:
                body = comment.get("body", "")
                if body and MARKER in body:
                    comment_id = comment.get("id")
                    if comment_id is not None:
                        return int(comment_id)
    except Exception as exc:
        logger.warning("Failed to search existing comments: %s", exc)
    return None


def upsert_comment(
    api_url: str,
    repo: str,
    pr_number: int,
    token: str,
    body: str,
) -> None:
    """Post or update the PR comment.

    Args:
        api_url: GitHub API URL.
        repo: Repository owner/name.
        pr_number: Pull request number.
        token: GitHub Token.
        body: The comment body markdown.
    """
    comment_id = find_existing_comment(api_url, repo, pr_number, token)

    if comment_id is not None:
        url = f"{api_url}/repos/{repo}/issues/comments/{comment_id}"
        logger.info("Updating existing comment %d", comment_id)
        github_request(url, token, "PATCH", {"body": body})
        logger.info("Successfully updated comment.")
    else:
        url = f"{api_url}/repos/{repo}/issues/{pr_number}/comments"
        logger.info("Creating a new comment on PR %d", pr_number)
        github_request(url, token, "POST", {"body": body})
        logger.info("Successfully created new comment.")


def parse_arguments(args: Sequence[str]) -> argparse.Namespace:
    """Parses command-line arguments.

    Args:
        args: Command-line arguments.

    Returns:
        argparse.Namespace: Parsed arguments.
    """
    parser = argparse.ArgumentParser(
        description="Post test gate results to PR comments."
    )
    parser.add_argument(
        "--results-file",
        default="test_results.json",
        help="Path to the test results JSON file.",
    )
    parser.add_argument(
        "--status",
        default="success",
        help="Status of the preceding job steps.",
    )
    parser.add_argument(
        "--pr-number",
        type=int,
        help="Explicit PR number (overrides GITHUB_EVENT_PATH).",
    )
    return parser.parse_args(args)


def main(argv: Sequence[str]) -> None:
    """Main execution function.

    Args:
        argv: Command-line arguments.
    """
    args = parse_arguments(argv)
    results_path = Path(args.results_file)

    token = os.environ.get("GITHUB_TOKEN")
    repo = os.environ.get("GITHUB_REPOSITORY")
    run_id = os.environ.get("GITHUB_RUN_ID")
    event_path = os.environ.get("GITHUB_EVENT_PATH")
    api_url = os.environ.get("GITHUB_API_URL", "https://api.github.com")
    server_url = os.environ.get("GITHUB_SERVER_URL", "https://github.com")

    if not token:
        logger.error("GITHUB_TOKEN environment variable is not set. Exiting.")
        sys.exit(1)

    if not repo:
        logger.error("GITHUB_REPOSITORY environment variable is not set. Exiting.")
        sys.exit(1)

    if not run_id:
        logger.error("GITHUB_RUN_ID environment variable is not set. Exiting.")
        sys.exit(1)

    pr_number = args.pr_number
    if pr_number is None:
        pr_number = get_pr_number(event_path)

    if pr_number is None:
        logger.error("Could not determine PR number. Exiting.")
        sys.exit(1)

    logger.info("Processing PR comment for repository %s, PR #%d", repo, pr_number)

    results = parse_results(results_path)
    body = generate_comment_body(
        results=results,
        job_status=args.status,
        repo=repo,
        run_id=run_id,
        server_url=server_url,
    )

    try:
        upsert_comment(
            api_url=api_url,
            repo=repo,
            pr_number=pr_number,
            token=token,
            body=body,
        )
    except Exception as exc:
        logger.error("Failed to upsert comment: %s", exc)
        sys.exit(1)


if __name__ == "__main__":
    main(sys.argv[1:])
