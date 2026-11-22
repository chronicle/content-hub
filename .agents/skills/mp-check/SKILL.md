---
name: mp-check
description: Lints Python files with ruff and runs static type analysis with ty for Content Hub integrations and packages. Use when checking Python code quality, auto-fixing lint violations, or running static type checks. Don't use for pure code formatting (use mp-format) or YAML and metadata schema validation (use mp-validate).
---

# `mp check` Skill

Runs `ruff check` (and optionally `ty check`) across Python files, directories, or named integrations.

> **Invocation**: Run `mp ...` if installed on `PATH` (`wmp` on Windows), or `uv run --frozen --project packages/mp mp ...` from the `content-hub` repository root (see `mp` skill [SKILL.md](../mp/SKILL.md)).

## Exact Command Syntax

```bash
mp check [OPTIONS] [FILE_PATHS]...
```

| Argument / Option | Behavior |
| :--- | :--- |
| `FILE_PATHS...` | Positional `.py` file paths, directory paths, or bare integration directory names. Mutually exclusive with `--changed-files` (at least one is required). Non-Python file paths are ignored. |
| `--output-format <FMT>` | `concise`, `full` (default), `json`, `json-lines`, `junit`, `grouped`, `github`, `gitlab`, `pylint`, `rdjson`, `azure`, `sarif`. |
| `--fix` | Applies safe `ruff` autofixes. |
| `--unsafe-fixes` | Applies unsafe `ruff` autofixes (requires `--fix` or raises `BadParameter`). |
| `--changed-files` | Checks files from `git diff HEAD^ HEAD --name-only --diff-filter=ACMRTUXB` (last commit only). |
| `--static-type-check` | Runs `ty check` after `ruff check`. |
| `--raise-error-on-violations` | Converts `LinterWarning` / `TypeCheckerWarning` into errors (exit code `1`). |
| `--quiet` / `--verbose` | Long-form options only (`-q` and `-v` are rejected on `mp check`, and root `mp -v check` is overwritten by `check`'s defaults). |

## Agentic Workflow

1. **Run deterministic check with compact output and strict exit code**:
   Always pass explicit `FILE_PATHS`, `--raise-error-on-violations`, and `concise` or `json` output so violations fail with exit code `1` and exact line locations:
   ```bash
   mp check <path_to_integration_or_py_files> --static-type-check --raise-error-on-violations --output-format concise
   ```
   **Done when:** Output lists exact diagnostics (or prints `All checks passed!` and exits `0`).

2. **Apply safe autofixes if needed, then re-verify**:
   ```bash
   mp check <path_to_integration_or_py_files> --fix
   mp check <path_to_integration_or_py_files> --static-type-check --raise-error-on-violations --output-format concise
   ```
   *(If `--unsafe-fixes` is used, inspect every changed hunk with `git diff` afterward.)*
   **Done when:** Re-verification exits `0` with zero lint and type diagnostics.

## Key Gotchas

- **Exits `0` on violations by default**: Without `--raise-error-on-violations`, `mp check` emits a Python `RuntimeWarning` (`LinterWarning` / `TypeCheckerWarning`) and still returns exit code `0`. Always pass `--raise-error-on-violations` in automated loops.
- **`--changed-files` only checks `HEAD^..HEAD`**: Uncommitted edits in the working tree or index are skipped by `--changed-files`. Pass explicit `.py` file or directory paths instead.
- **Hierarchical `ruff.toml` rule tiers**: `ruff` resolves configuration per target file: `content/response_integrations/google/ruff.toml` enforces `ALL`, `content/response_integrations/third_party/ruff.toml` enforces `E,F,FA102,I`, and the root `ruff.toml` (`E,F,CPY,FA102,I`) covers `power_ups/` and shared areas unless a nearer `ruff.toml` overrides it.
