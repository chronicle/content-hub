---
name: mp-format
description: Formats Python source files in Content Hub integrations and packages using the mp formatter wrapper. Use when formatting modified Python files or normalizing code style before linting or committing. Don't use for lint rule violations or static type checks (use mp-check).
---

# `mp format` Skill

Runs `ruff format` on target Python files, directories, or named integrations.

> **Invocation**: Run `mp ...` if installed on `PATH` (`wmp` on Windows), or `uv run --frozen --project packages/mp mp ...` from the `content-hub` repository root (see `mp` skill [SKILL.md](../mp/SKILL.md)).

## Exact Command Syntax

```bash
mp format [OPTIONS] [FILE_PATHS]...
```

| Argument / Option | Behavior |
| :--- | :--- |
| `FILE_PATHS...` | Positional `.py` file paths, directory paths, or bare integration directory names (for example, `active_directory`). Non-Python file paths are ignored. |
| `--changed-files` | Formats files returned by `git diff HEAD^ HEAD --name-only --diff-filter=ACMRTUXB` (last commit only). |
| `--quiet` | Suppresses standard progress logs (long option only; no `-q` shorthand). |
| `--verbose` | Enables debug logging (long option only; no `-v` shorthand). |

## Agentic Workflow

1. **Scope strictly to touched files or a new integration directory**:
   Pass explicit `.py` file paths (preferred when modifying an existing integration or package so untouched legacy files are not reformatted) or the target directory:
   ```bash
   mp format <path/to/modified_file1.py> <path/to/modified_file2.py>
   # Or for a newly created integration directory:
   mp format content/response_integrations/third_party/community/<integration_name>
   ```
   **Done when:** Command exits `0` with no `FormatterWarning` emitted.

2. **Verify clean diff scope**:
   Run `git diff --stat` to confirm only files belonging to the current task were reformatted (PR review rules reject unrelated reformat-only hunks).
   **Done when:** Only intended files appear in `git status --short`.

## Key Gotchas

- **`--changed-files` ignores uncommitted edits**: `mp format --changed-files` diffs `HEAD^` against `HEAD` (the last committed change), **not** unstaged/staged working-tree changes and **not** `origin/main`. Always pass explicit `FILE_PATHS` before committing.
- **Empty or non-Python paths are silent no-ops**: Running `mp format` with no arguments, or passing a non-Python file path such as `.../my_integration/definition.yaml`, logs `"No files found to check"` or `"No relevant python files to format"` and exits `0` without formatting anything.
- **No `-q`/`-v` shorthands, and root `-v` is reset**: `mp format -v` fails with `No such option`, and `mp -v format ...` is overwritten by `format`'s default `verbose=False`. Pass `mp format --verbose ...` when debug output is needed.
