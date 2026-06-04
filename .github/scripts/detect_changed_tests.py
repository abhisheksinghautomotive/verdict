#!/usr/bin/env python3
"""Detect changed test files between two git refs.

This script executes a git diff between a base branch and a head ref,
filters the changed files for test files matching 'app/tests/test_*.py',
and writes the results to the GITHUB_OUTPUT environment variable file.
"""

import argparse
import fnmatch
import json
import logging
import os
import subprocess
import sys
from typing import Sequence


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
logger = logging.getLogger("detect-changed-tests")
handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(JsonFormatter())
logger.addHandler(handler)
logger.setLevel(logging.INFO)


def run_git_diff(base: str, head: str) -> list[str]:
    """Runs git diff to find changed files between the base ref and head ref.

    Args:
        base: The base git ref (e.g. main or origin/main).
        head: The head git ref (e.g. HEAD or a commit SHA).

    Returns:
        list[str]: A list of changed file paths relative to the repository root.

    Raises:
        RuntimeError: If the git diff command fails.
    """
    logger.info("Running git diff between %s and %s", base, head)
    cmd = ["git", "diff", "--name-only", f"{base}...{head}"]
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True,
        )
        changed_files = [
            line.strip() for line in result.stdout.splitlines() if line.strip()
        ]
        return changed_files
    except subprocess.CalledProcessError as err:
        logger.error(
            "Git diff command failed. Code: %d, Stderr: %s",
            err.returncode,
            err.stderr,
        )
        raise RuntimeError(f"Git diff failed: {err.stderr}") from err


def write_github_output(github_output_path: str, key: str, value: str) -> None:
    """Writes a key-value pair to the GITHUB_OUTPUT file.

    Args:
        github_output_path: The file path to the GITHUB_OUTPUT file.
        key: The output variable name.
        value: The output variable value.

    Raises:
        IOError: If writing to the file fails.
    """
    logger.info("Writing output: %s=%s", key, value)
    with open(github_output_path, "a", encoding="utf-8") as f:
        f.write(f"{key}={value}\n")


def parse_arguments(args: Sequence[str]) -> argparse.Namespace:
    """Parses command-line arguments.

    Args:
        args: Command-line arguments.

    Returns:
        argparse.Namespace: Parsed arguments containing base and head.
    """
    parser = argparse.ArgumentParser(
        description="Detect changed test files between two git refs."
    )
    parser.add_argument(
        "--base",
        required=True,
        help="The base git ref (e.g. main or origin/main).",
    )
    parser.add_argument(
        "--head",
        required=True,
        help="The head git ref (e.g. HEAD or a commit SHA).",
    )
    return parser.parse_args(args)


def main(argv: Sequence[str]) -> None:
    """Main execution function.

    Args:
        argv: Command-line arguments.
    """
    args = parse_arguments(argv)

    try:
        changed_files = run_git_diff(args.base, args.head)
    except Exception:
        logger.exception("Failed to detect changed files")
        sys.exit(1)

    # Filter files matching app/tests/test_*.py
    changed_tests = fnmatch.filter(changed_files, "app/tests/test_*.py")

    logger.info("Total changed files: %d", len(changed_files))
    logger.info("Detected changed tests: %s", changed_tests)

    # Set outputs for GitHub Actions
    github_output_path = os.environ.get("GITHUB_OUTPUT")

    changed_tests_str = " ".join(changed_tests)
    changed_tests_json = json.dumps(changed_tests)
    has_changed_tests = str(len(changed_tests) > 0).lower()

    if github_output_path:
        logger.info(
            "GITHUB_OUTPUT is set. Appending outputs to: %s", github_output_path
        )
        try:
            write_github_output(github_output_path, "changed_tests", changed_tests_str)
            write_github_output(
                github_output_path, "changed_tests_json", changed_tests_json
            )
            write_github_output(
                github_output_path, "has_changed_tests", has_changed_tests
            )
        except IOError as exc:
            logger.error("Failed to write to GITHUB_OUTPUT: %s", exc)
            sys.exit(1)
    else:
        logger.info("GITHUB_OUTPUT is not set. Output writing skipped.")


if __name__ == "__main__":
    main(sys.argv[1:])
