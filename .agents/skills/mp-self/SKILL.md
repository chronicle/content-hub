---
name: mp-self
description: Upgrades a standalone mp CLI installation from the chronicle/content-hub main branch. Use when the user asks to self-update an installed mp binary or resolve an outdated mp version warning emitted at exit. Don't use inside a local packages/mp development virtualenv where local source edits would be overwritten.
---

# `mp self` Skill

Upgrades `mp` in its active Python interpreter environment by executing `<sys.executable> -m uv pip install --upgrade git+https://github.com/chronicle/content-hub.git#subdirectory=packages/mp`.

## How `mp` Update Checks Work

On every CLI invocation, `mp` starts a background `UpdateChecker` daemon thread (`mp.core.update_checker`) that fetches `packages/mp/pyproject.toml` from `https://raw.githubusercontent.com/chronicle/content-hub/main/packages/mp/pyproject.toml` (2-second timeout) and logs a warning at `atexit` if the remote `main` version exceeds `importlib.metadata.version("mp")`.

## Exact Command Syntax

```bash
mp self update
```

## Agentic Workflow

1. **Identify which Python environment owns `mp`**:
   Record the active binary path and current version before upgrading:
   ```bash
   which mp   # On Windows: where wmp
   mp --version
   ```
   - **Local checkout guard**: If you are invoking `uv run --project packages/mp mp ...` or the active `mp` binary lives inside `<content-hub>/packages/mp/.venv/`, **stop and do not run `mp self update`**. Running `mp self update` inside `packages/mp/.venv` overwrites the editable local `packages/mp` package with remote `origin/main` until `uv sync --dev --project packages/mp` is re-run.
   - **Standalone install**: If `mp` is installed as a standalone tool (for example, `~/.local/bin/mp` via `uv tool install`), proceed to step 2.
   **Done when:** Active `mp` binary is confirmed to be a standalone installation outside `packages/mp/.venv`.

2. **Side-effect gate, execute upgrade, and verify `uv` output**:
   Confirm with the user before mutating their global `mp` installation, then run:
   ```bash
   mp self update
   mp --version
   ```
   *(For `uv tool` installations, `uv tool upgrade mp` is an equivalent alternative.)*
   - **Check subprocess output carefully**: `execute_command_and_get_output` streams `uv pip install` output and returns its exit code without raising on non-zero status, so `"Successfully updated mp!"` can print even if `uv` logged a network or wheel error. Inspect the streamed `uv` lines for errors and confirm `mp --version` reflects the expected version.
   **Done when:** Streamed `uv` output shows zero errors and `mp --version` prints the updated version.

## Key Gotchas

- **Ignore update warnings during local branch testing**: When testing a local `packages/mp` branch behind `origin/main`, ignore the `atexit` update warning; rebase on `origin/main` and run `uv sync --dev --project packages/mp` instead.
- **Network & Windows notes**: Requires HTTPS access to `github.com` and `pypi.org`. On Windows, invoke `wmp self update` (or `uv tool upgrade mp` if Windows locks `wmp.exe` during upgrade).
