#!/usr/bin/env python3
"""Post Terraform plan results as a sticky comment on a GitHub PR."""

import argparse
import json
import logging
import os
import re
import sys
import urllib.request
import urllib.error
from pathlib import Path
from typing import Any, Sequence, Tuple

MARKER = "<!-- verdict-tf-plan -->"
MAX_COMMENT_LENGTH = 60000


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
logger = logging.getLogger("post-tf-plan")
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
        # Fallback for raw issue fields
        num = event_data.get("number")
        if num is not None:
            return int(num)
    except Exception as exc:
        logger.warning("Failed to parse event payload: %s", exc)
    return None


def parse_plan_file(plan_path: Path) -> Tuple[int, int, int, str]:
    """Parse the Terraform plan file to extract changes summary and raw content.

    Args:
        plan_path: Path to the plan output text file.

    Returns:
        Tuple[int, int, int, str]: Added, changed, destroyed counts and the raw content.
    """
    if not plan_path.exists():
        logger.warning("Plan file not found at %s", plan_path)
        return 0, 0, 0, ""
    try:
        content = plan_path.read_text(encoding="utf-8")
    except Exception as exc:
        logger.error("Failed to read plan file: %s", exc)
        return 0, 0, 0, ""

    added, changed, destroyed = 0, 0, 0
    # Match pattern: "Plan: X to add, Y to change, Z to destroy."
    plan_match = re.search(
        r"Plan:\s*(\d+)\s*to\s*add,\s*(\d+)\s*to\s*change,\s*(\d+)\s*to\s*destroy",
        content,
    )
    if plan_match:
        added = int(plan_match.group(1))
        changed = int(plan_match.group(2))
        destroyed = int(plan_match.group(3))
    elif "No changes. Your infrastructure matches the configuration." in content:
        logger.info("Plan summary: No changes.")
    else:
        logger.warning("Could not identify plan summary in plan content.")

    return added, changed, destroyed, content


def generate_comment_body(
    added: int,
    changed: int,
    destroyed: int,
    plan_content: str,
    repo: str,
    run_id: str,
    server_url: str,
) -> str:
    """Generate the markdown comment body summarizing the Terraform plan.

    Args:
        added: Count of resources to add.
        changed: Count of resources to change.
        destroyed: Count of resources to destroy.
        plan_content: Raw plan file content.
        repo: Owner/repository path.
        run_id: Workflow run ID.
        server_url: GitHub server URL.

    Returns:
        str: Markdown formatted comment body.
    """
    run_url = f"{server_url}/{repo}/actions/runs/{run_id}"

    # Handle empty or missing plan content
    if not plan_content.strip():
        return f"""{MARKER}
## Verdict Infrastructure Deployment Plan

| Metric | Value |
| :--- | :--- |
| **Verdict** | 🔴 PLAN FAILURE |
| **Details** | Terraform plan execution failed or produced empty output. |
| **Workflow Run** | [Run #{run_id}]({run_url}) |
"""

    summary_verdict = "🟢 NO CHANGES"
    if added > 0 or changed > 0 or destroyed > 0:
        summary_verdict = f"🟡 CHANGES PLANNED (+{added}, ~{changed}, -{destroyed})"

    # Truncate plan content if it exceeds the maximum comment length limit
    if len(plan_content) > MAX_COMMENT_LENGTH:
        truncated_msg = f"\n\n... [Plan output truncated; exceeded {MAX_COMMENT_LENGTH} char limit] ..."
        plan_content = plan_content[:MAX_COMMENT_LENGTH] + truncated_msg

    body = f"""{MARKER}
## Verdict Infrastructure Deployment Plan

| Action | Count |
| :--- | :--- |
| **Status** | {summary_verdict} |
| ➕ **Add** | {added} |
| 🔄 **Change** | {changed} |
| ❌ **Destroy** | {destroyed} |
| **Workflow Run** | [Run #{run_id}]({run_url}) |

<details>
<summary><b>Detailed Terraform Plan Output</b></summary>

```terraform
{plan_content}
```

</details>
"""
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
    req.add_header("User-Agent", "verdict-tf-plan-gha")

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
    parser = argparse.ArgumentParser(description="Post Terraform plan to PR comments.")
    parser.add_argument(
        "--plan-file",
        required=True,
        help="Path to the Terraform plan text file.",
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
    plan_path = Path(args.plan_file)

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

    added, changed, destroyed, plan_content = parse_plan_file(plan_path)
    body = generate_comment_body(
        added=added,
        changed=changed,
        destroyed=destroyed,
        plan_content=plan_content,
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
