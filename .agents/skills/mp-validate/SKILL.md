---
name: mp-validate
description: Validates Content Hub response integrations, playbooks, or full repositories against pre-build structural, metadata, dependency, and release-hygiene rules. Use when checking YAML definitions, release notes, version bumps, lockfile consistency, or playbook schemas before building or opening a PR. Don't use for Python linting or type-checking (use mp-check) or live server view preflight checks (use mp-push).
---

# `mp validate` Skill

Executes parallel pre-build validators on non-built integrations (23 rules) and playbooks (10 rules).

> **Invocation & Prerequisite**: Run `mp ...` (`wmp` on Windows) or `uv run --frozen --project packages/mp mp ...` from the `content-hub` root, and ensure `mp config --display-config` points `Marketplace path` to `content-hub` (see `mp-config` skill [SKILL.md](../mp-config/SKILL.md)).

## Exact Command Syntax

Use the subcommands (`integration`, `playbook`, `repository`); flag-based `mp validate -i/-p/-r` is deprecated.

```bash
BROWSER=true mp validate integration <INTEGRATION_NAMES>... [--quiet|-q] [--verbose|-v]
BROWSER=true mp validate playbook <PLAYBOOK_NAMES>... [--quiet|-q] [--verbose|-v]
BROWSER=true mp validate repository <google|third_party|playbooks|all_content>... [--quiet|-q] [--verbose|-v]
```

- Pass integration or playbook **directory names** (for example, `telegram`), not filesystem paths (`content/response_integrations/.../telegram` will not match).

## Agentic Workflow

1. **Suppress browser launch and enable version-bump validation when committed**:
   - **Prevent browser hang (`BROWSER=true`)**: Unless `GITHUB_ACTIONS=true` is set, `mp validate` writes a temporary HTML report and calls `webbrowser.open()` on every run (even when all checks pass), which can block headless TTY shells on `lynx`/`www-browser`. Always prefix with `BROWSER=true`.
   - **Enable `Version Bump` checks locally (`GITHUB_PR_SHA`)**: Both integration and playbook `VersionBumpValidation` return immediately as a no-op unless `GITHUB_PR_SHA` is set in the environment! Once your changes are committed on a local branch (and `origin/main` is fetched), pass `GITHUB_PR_SHA=$(git rev-parse HEAD)` so `mp validate` diffs against `origin/main` just like CI.
   **Done when:** `BROWSER=true` (and `GITHUB_PR_SHA` when testing a committed branch) is set.

2. **Run targeted validation and confirm non-empty coverage**:
   ```bash
   BROWSER=true mp validate integration <integration_name>
   # Once changes are committed on your branch:
   BROWSER=true GITHUB_PR_SHA=$(git rev-parse HEAD) mp validate integration <integration_name>
   ```
   **Done when:** Command exits `0` (exits `1` if any validation fails) **and** you verify the target wasn't silently skipped due to a misspelled name.

3. **Resolve reported rule failures**:
   - **`Uv Lock`**: Run `uv lock --project <integration_dir>` so `uv.lock` matches `pyproject.toml`.
   - **`Integration Version Bump` / `Version Consistency` / `Release Notes Date`**: Modified integrations must increment `version` in `pyproject.toml` by `+1.0`, add matching `version:` entries in `release_notes.yaml` with `publish_time` formatted as `YYYY-MM-DD`, and keep versions consistent across `pyproject.toml` and `release_notes.yaml`.
   - **`Required Dev Dependencies` / `Verify SSL` / `Ping` / `Json Result Example`**: Ensure `soar-sdk`, `pytest`, and `pytest-json-report` are in `dev` dependencies, `Verify SSL` and `Ping` exist, and `resources/<action>_JsonResult_example.json` is present.
   **Done when:** Re-running `mp validate` exits `0` with zero failed validations.

## Key Gotchas

- **Misspelled names exit `0` silently**: Passing an unknown name (or a path instead of a directory name) prints `"All Validations Passed"` with 0 items checked and exits `0`. Verify `<integration_name>` or `<playbook_name>` actually exists under `content/` before trusting a clean exit.
- **Parsers are separate**: SIEM parsers under `content/parsers/` are validated with `tools/parsers/`, not `mp validate`.
