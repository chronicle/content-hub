# Content-Hub Python Style Guide

## Introduction

This style guide outlines the coding conventions for Python code developed for the **Content-Hub**
open-source repository within Google SecOps.

Our mission is to ensure that all contributions are not just **functionally correct**, but *
*production-ready**. This means prioritizing security, observability, and resilient design patterns
that can withstand the demands of a Security Operations environment.

---

## Key Principles

* **Production-Ready SecOps:** Code must be resilient. Implement defensive programming, proactive
  error handling, and structured logging.
* **Security-First:** Python code must be hardened against intent-based or accidental misuse.
* **Readability & Maintainability:** Code is read more often than it is written. Use clear,
  descriptive naming and modular logic.
* **Performance:** Efficiency is critical in high-throughput environments. Avoid blocking calls in
  asynchronous contexts.
* **PII & Secret Sanitization:** Never allow Personally Identifiable Information (PII) or secrets to
  persist in logs, metadata, or telemetry.
    * **No Hardcoded Secrets:** Use secret managers for keys and tokens.
    * **Log Redaction:** Mask sensitive data fields before outputting to logs.
    * **Data Minimization:** Process only the absolute minimum data required for the operation.

---

## Security & Reliability

### Safe Path Handling

* **Mandatory `pathlib`:** Always use `pathlib.Path` for file system operations.
* **Avoid String Concatenation:** Do not use raw string concatenation (e.g., `folder + "/" + file`)
  or `os.path.join`.

> **Gemini Action:** Proactively suggest refactoring any manual path manipulation to use
`pathlib.Path` objects and the `/` operator.

### Input & Execution Safety

* **No f-string SQL queries:** Always use parameterized queries to prevent SQL injection.
* **Safe Loading:** Use `yaml.safe_load()` instead of `yaml.load()` and `json.loads()` to prevent
  arbitrary code execution.

### Path-Specific Security Enforcement

The following rules need to be tracked and reported in the following path: "
content/response_integrations/**"

* **No Shell Execution:** Avoid `subprocess.run(..., shell=True)`. Always provide arguments as a
  list to prevent shell injection.
* **Prohibited Functions:** Use of `eval()`, `exec()`, or `input()` is strictly forbidden in
  production logic.

### Logging & Observability

* **No PII in Logs:** Never log secrets, API keys, tokens, or Personally Identifiable Information (
  PII).

---

## Modern Python Patterns

### Asynchronous Programming

Since many SecOps workflows are I/O bound (API calls, logs), we leverage `asyncio`.

* **Non-blocking I/O:** Use `async` and `await` for network requests (e.g., using `httpx` or
  `aiohttp`).
* **Avoid Blocking Calls:** Never use `time.sleep()` or blocking socket operations inside an
  `async def` function. Use `asyncio.sleep()`.
* **Concurrency:** Use `asyncio.gather` for parallel I/O tasks where appropriate to improve
  performance.

### Static Type Checking

* **Strictness:** All function parameters and return types **must** be annotated.
* **Modern Syntax:** Use the pipe operator for unions (e.g., `str | None`) instead of `Optional` (
  Python 3.10+).

---

## Docstrings & Documentation

We follow the **Google Style Docstrings** with a focus on reducing "stale" information.

* **Triple Double Quotes:** Use `"""Docstring"""` for all modules, classes, and functions.
* **No Redundant Types:** Do **not** repeat types in the `Args` or `Returns` sections. Types should
  be inferred from the function signature's type hints.
* **Mandatory "Raises":** Explicitly document all exceptions that the function may intentionally
  raise.

```python
from pathlib import Path
from typing import Any


def process_hub_config(config_path: Path, retry_count: int = 3) -> dict[str, Any]:
    """Processes the central hub configuration file.

    Args:
        config_path: The filesystem path to the YAML configuration.
        retry_count: Number of attempts to read the file if busy.

    Returns:
        A dictionary representing the validated configuration.

    Raises:
        FileNotFoundError: If the config_path does not exist.
        RuntimeError: If the configuration is malformed or inaccessible.
    """
    if not config_path.exists():
        raise FileNotFoundError(f"Missing config at: {config_path}")

    # Body implementation...
    return {}
```

---

## Integration-Specific Requirements

> **Gemini Action:** The following rules apply **strictly** to changes made within the
`content/response_integrations/**` directory.

### Testing

All new features, bug fixes, or integrations added to `content/response_integrations/**` **must**
include corresponding unit tests to ensure production stability.

* **Framework:** Use `pytest` for test execution.
* **Reference Examples:** When generating or suggesting tests, Gemini **must** model the code after
  the **"Golden Tests"** found in:
    * `content/response_integrations/third_party/telegram/tests/`
    * `content/response_integrations/third_party/sample_integration/tests/`
* **Mocking:** Follow the mocking patterns established in the reference examples above. **Strict
  Rule:** Never make real network calls during unit tests.

> **Gemini Action:** If a contributor modifies or adds files in this path, check for a corresponding
> test file. If missing or incomplete, suggest generating a test suite modeled specifically after the
> patterns found in the Telegram or Sample Integration reference paths.

### Validation & JSON Results

For integrations utilizing the `TIPCommon` Action base class or standard result reporting, we
require explicit documentation of the output schema.

* **Detection:** Identify if an action returns a JSON result by looking for:
    * Calls to `result.add_result_json(...)`
    * Assignments to `self.soar_action.json = ...`
    * Assignments to `self.json_results = ...`
* **Requirement:** If a JSON result is detected, a corresponding JSON example file **must** exist in
  the integration's `resources/` directory.
* **Naming Convention:** The example file must match the action's filename (e.g., `action_name.py`
  or `action_name.yaml` requires `resources/action_name_json_example.json`).

> **Gemini Action:** If a JSON result assignment is detected but the corresponding
`_json_example.json` file is missing in the `resources/` folder, alert the contributor and offer to
> generate a placeholder JSON structure based on the code's logic.

---