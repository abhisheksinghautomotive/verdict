# PR Gate Execution Demo & Runbook

This document records the end-to-end verification of the GitHub Actions PR Test Gating pipeline. It provides proof of the gating behavior, verifying that:
1. A pull request with passing tests successfully clears the gate (status green).
2. A pull request with failing tests fails the gate (status red, merge blocked) and posts diagnostic logs directly to the PR comments.

---

## 🟢 Scenario 1: Passing Pull Request

**Branch Name**: `feat/issue-30-passing-gate`  
**Pull Request**: [#67](https://github.com/abhisheksinghautomotive/verdict/pull/67)  
**Workflow Run**: [Run #26965948617](https://github.com/abhisheksinghautomotive/verdict/actions/runs/26965948617)  
**Status**: `SUCCESS`  

### Description
A single passing test was added to the repository:

```python
# app/tests/test_dummy_pass.py
"""Dummy passing test for testing CI/CD PR gating flow."""


def test_ok() -> None:
    """A dummy test that always passes."""
    assert True
```

### Resulting PR Comment
The workflow executed, deployed the service to the EKS dev cluster, ran the test suite, and posted the following summary comment:

```markdown
<!-- verdict-test-gate -->
## Verdict Test Gate Results

| Metric | Value |
| :--- | :--- |
| **Verdict** | 🟢 **🟢 PASS** |
| **Total Test Files** | 1 |
| **Passed** | 1 |
| **Failed** | 0 |
| **Workflow Run** | [Run #26965948617](https://github.com/abhisheksinghautomotive/verdict/actions/runs/26965948617) |
```

---

## 🔴 Scenario 2: Failing Pull Request

**Branch Name**: `feat/issue-30-failing-gate`  
**Pull Request**: [#68](https://github.com/abhisheksinghautomotive/verdict/pull/68)  
**Workflow Run**: [Run #26966129235](https://github.com/abhisheksinghautomotive/verdict/actions/runs/26966129235)  
**Status**: `FAILURE`  

### Description
A single failing test was added to the repository:

```python
# app/tests/test_dummy_fail.py
"""Dummy failing test for testing CI/CD PR gating flow."""


def test_fail() -> None:
    """A dummy test that always fails."""
    assert False
```

### Resulting PR Comment & Diagnostics
The workflow failed on test execution and posted a rich comment with the test run summary and collapsible execution log for quick diagnostics:

```markdown
<!-- verdict-test-gate -->
## Verdict Test Gate Results

| Metric | Value |
| :--- | :--- |
| **Verdict** | 🔴 **🔴 FAIL** |
| **Total Test Files** | 1 |
| **Passed** | 0 |
| **Failed** | 1 |
| **Workflow Run** | [Run #26966129235](https://github.com/abhisheksinghautomotive/verdict/actions/runs/26966129235) |

### 🔴 Failing Test Files

| File | Status | Duration |
| :--- | :--- | :--- |
| `app/tests/test_dummy_fail.py` | `fail` | 6039ms |

### 🔍 Execution Logs for Failed Tests

<details>
<summary><b>Logs: app/tests/test_dummy_fail.py</b></summary>

```
============================= test session starts ==============================
platform linux -- Python 3.12.13, pytest-9.0.3, pluggy-1.6.0
rootdir: /app
plugins: anyio-4.13.0
collected 1 item

app/tests/test_dummy_fail.py F                                           [100%]

=================================== FAILURES ===================================
__________________________________ test_fail ___________________________________

    def test_fail() -> None:
        """A dummy test that always fails."""
>       assert False
E       assert False

app/tests/test_dummy_fail.py:6: AssertionError
...
=========================== short test summary info ============================
FAILED app/tests/test_dummy_fail.py::test_fail - assert False
======================== 1 failed, 2 warnings in 0.19s =========================
```
```
```

### Merge Blocked Enforcement
Because `main` is protected by ruleset `protect-main` which requires the `PR Test Gate` check to pass before merging:
- Pull Request #67 had the green check and permitted merging.
- Pull Request #68 failed the status check, preventing squash-merging and blocking any merge attempt.
