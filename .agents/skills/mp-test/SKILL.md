---
name: mp-test
description: Runs pre-build pytest suites for Content Hub response integrations in isolated per-integration virtual environments. Use when executing unit tests for one or more integrations or an entire integration repository tier. Don't use for unit-testing the mp Python package itself or validating playbook schemas (use mp-validate).
---

# `mp test` Skill

Executes per-integration `pytest` suites in parallel via `run_pre_build_tests.sh` (or `.bat` on Windows), adding `soar_sdk` from each integration's `.venv` to `PYTHONPATH` and summarizing results.

> **Invocation & Prerequisite**: Run `mp ...` (`wmp` on Windows) or `uv run --frozen --project packages/mp mp ...` from the `content-hub` root, and ensure `mp config --display-config` points `Marketplace path` to `content-hub` (see `mp-config` skill [SKILL.md](../mp-config/SKILL.md)).

## Exact Command Syntax

Unlike `mp build` and `mp validate`, `mp test` has **no subcommands**. Pass `--integration` (`-i`) or `--repository` (`-r`) directly (exactly one of the two is required):

```bash
BROWSER=true mp test --integration <INTEGRATION_NAME> [--integration <OTHER_NAME>...] [--raise-error-on-violations] [--quiet|-q] [--verbose|-v]
BROWSER=true mp test --repository <google|third_party> [--raise-error-on-violations] [--quiet|-q] [--verbose|-v]
```

## Agentic Workflow

1. **Refresh the integration `.venv` if dependencies changed**:
   `run_pre_build_tests.sh` skips `uv sync --dev` whenever `<integration_dir>/.venv` already exists on disk. If `pyproject.toml` or `uv.lock` was modified, sync the integration's environment first:
   ```bash
   uv sync --dev --project <integration_dir>
   ```
   **Done when:** `<integration_dir>/.venv` reflects current `pyproject.toml` and `uv.lock`.

2. **Run `mp test` with `BROWSER=true` and verify execution count**:
   Unless `GITHUB_ACTIONS=true` is set, `mp test` writes a temp HTML report and calls `webbrowser.open()` on every run (even on pass), which can block headless TTY shells on `lynx`/`www-browser`. Always prefix with `BROWSER=true`:
   ```bash
   BROWSER=true mp test --integration <integration_name> --verbose
   ```
   **Done when:** `mp test` exits `0` **and** logs `Integration: <integration_name> | Passed: <N> | Executed: <N> / <N> collected` (confirming the integration was found and its tests ran).

3. **Check for interrupted `.report.json` leftovers**:
   Normally `mp test` parses and deletes `<integration_dir>/.report.json` automatically; if a run was killed mid-execution, remove any leftover `<integration_dir>/.report.json` since it is not gitignored.
   **Done when:** `git status --short <integration_dir>` shows no `.report.json` file.

## Key Gotchas

- **No `integration` subcommand**: `mp test integration foo` fails with an unexpected extra argument error. Always use `mp test -i foo`.
- **Unknown names exit `0` silently**: Passing a misspelled integration name (or a path instead of the exact folder name, or `http` instead of `http_integration` / `twilio` instead of `twilio_integration`) prints `"All Tests Passed"` and exits `0` without running anything. Always check for the `Integration: <name> | Passed:` log line.
- **`--repository` only tests `google` and `third_party`**: Passing `-r playbooks`, `-r custom`, or `-r all_content` is accepted by the enum parser but matches neither branch and exits `0` running 0 tests.
- **Pytest exit codes `{0, 2, 5}`**: Internally `mp test` treats pytest status `0` (all passed), `2` (interrupted with 0 failed), and `5` (zero tests collected) as non-failing when `failed_tests == 0`; any `failed_tests > 0` or venv/script setup failure exits `1`.
