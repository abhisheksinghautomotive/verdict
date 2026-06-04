#!/usr/bin/env python3
"""Execute test files on the remote EKS FastAPI app via port-forwarding."""

import argparse
import json
import logging
import subprocess
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path
from typing import Any, Sequence


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
logger = logging.getLogger("run-tests")
handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(JsonFormatter())
logger.addHandler(handler)
logger.setLevel(logging.INFO)


def start_port_forward() -> subprocess.Popen[str]:
    """Starts the kubectl port-forward subprocess.

    Returns:
        subprocess.Popen[str]: The port-forward process object.
    """
    logger.info(
        "Starting kubectl port-forward for service verdict-app in namespace verdict"
    )
    cmd = [
        "kubectl",
        "port-forward",
        "-n",
        "verdict",
        "svc/verdict-app",
        "8080:80",
    ]
    # Run port-forwarding in background. Redirect stdout to DEVNULL and
    # capture stderr to diagnose early exits without blocking.
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
    )
    return process


def wait_for_health_check(
    process: subprocess.Popen[str], timeout: float = 15.0
) -> bool:
    """Polls the health check endpoint until it returns 200 or timeout is reached.

    Args:
        process: The background port-forward process to monitor.
        timeout: Maximum time to wait in seconds.

    Returns:
        bool: True if health check succeeds, False otherwise.
    """
    start_time = time.perf_counter()
    url = "http://localhost:8080/health"
    logger.info("Waiting for health check to pass on %s", url)
    while time.perf_counter() - start_time < timeout:
        # Check if the process exited early
        if process.poll() is not None:
            stderr = ""
            if process.stderr:
                stderr = process.stderr.read().strip()
            logger.error(
                "kubectl port-forward exited early with code %d. Stderr: %s",
                process.returncode,
                stderr,
            )
            return False

        try:
            req = urllib.request.Request(url, method="GET")
            with urllib.request.urlopen(req, timeout=1.0) as response:
                if response.status == 200:
                    data = json.loads(response.read().decode("utf-8"))
                    if data.get("status") == "ok":
                        logger.info("Health check passed.")
                        return True
        except Exception:
            # Silence connection refused errors during bootstrap
            pass
        time.sleep(0.5)
    return False


def run_test_file(test_file: str) -> dict[str, Any]:
    """Sends a POST request to run the specified test file on the FastAPI app.

    Args:
        test_file: Path to the test file to run.

    Returns:
        dict[str, Any]: The run results containing status, stdout, and duration_ms.
    """
    url = "http://localhost:8080/run-test"
    logger.info("Triggering test run for file: %s", test_file)
    payload = json.dumps({"test_file": test_file}).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=120.0) as response:
            result: dict[str, Any] = json.loads(response.read().decode("utf-8"))
            return result
    except urllib.error.HTTPError as err:
        try:
            error_body = err.read().decode("utf-8")
            logger.error(
                "HTTP error during test execution for %s: %d - %s",
                test_file,
                err.code,
                error_body,
            )
            return {
                "status": "fail",
                "stdout": f"HTTP Error {err.code}: {error_body}",
                "duration_ms": 0,
            }
        except Exception:
            logger.error(
                "HTTP error during test execution for %s: %d",
                test_file,
                err.code,
            )
            return {
                "status": "fail",
                "stdout": f"HTTP Error {err.code}",
                "duration_ms": 0,
            }
    except Exception as exc:
        logger.exception(
            "Unexpected error during test execution for %s", test_file
        )
        return {
            "status": "fail",
            "stdout": f"Unexpected execution error: {str(exc)}",
            "duration_ms": 0,
        }


def write_results_file(output_path: Path, results: list[dict[str, Any]]) -> None:
    """Writes the test results list to a JSON file.

    Args:
        output_path: Path to the output JSON file.
        results: List of test run result dictionaries.
    """
    logger.info("Writing aggregated test results to %s", output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)


def parse_arguments(args: Sequence[str]) -> argparse.Namespace:
    """Parses command-line arguments.

    Args:
        args: Command-line arguments.

    Returns:
        argparse.Namespace: Parsed arguments.
    """
    parser = argparse.ArgumentParser(
        description="Run tests against verdict-app on EKS."
    )
    parser.add_argument(
        "test_files",
        nargs="+",
        help="Space-separated list of test files to run.",
    )
    parser.add_argument(
        "--output",
        default="test_results.json",
        help="Path to save the JSON results file.",
    )
    return parser.parse_args(args)


def main(argv: Sequence[str]) -> None:
    """Main execution function.

    Args:
        argv: Command-line arguments.
    """
    args = parse_arguments(argv)
    output_path = Path(args.output)
    test_files = args.test_files

    process = start_port_forward()
    results: list[dict[str, Any]] = []
    success = True

    try:
        if not wait_for_health_check(process):
            logger.error("Failed to connect to verdict-app. Aborting test run.")
            sys.exit(1)

        for test_file in test_files:
            result = run_test_file(test_file)
            result["test_file"] = test_file
            results.append(result)
            if result.get("status") != "pass":
                success = False

        write_results_file(output_path, results)

        passed = sum(1 for r in results if r.get("status") == "pass")
        failed = len(results) - passed
        logger.info("Execution Summary: %d passed, %d failed", passed, failed)

        if not success:
            logger.error("Some tests failed.")
            sys.exit(1)
        else:
            logger.info("All tests passed successfully.")
            sys.exit(0)

    finally:
        logger.info("Cleaning up port-forward process...")
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
        logger.info("Cleanup complete.")


if __name__ == "__main__":
    main(sys.argv[1:])
