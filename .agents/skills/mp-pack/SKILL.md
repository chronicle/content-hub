---
name: mp-pack
description: Packages a Content Hub response integration into a SOAR-importable ZIP archive, supporting custom beta identifiers and historical Git version packaging. Use when generating a standalone integration ZIP file for manual SOAR import or side-by-side beta testing. Don't use for raw out/ directory builds (use mp-build) or direct API uploads to a tenant (use mp-push).
---

# `mp pack` Skill

Builds an integration in a temporary directory, marks `IsCustom = true` in `Integration-*.def`, optionally checks out a historical integration version via a temporary Git worktree or renames identifiers for beta testing, and outputs `<identifier><YYYYMMDD>.zip` to `<marketplace_path>/out/pack/` (or `--dst`).

> **Invocation & Prerequisite**: Run `mp ...` (`wmp` on Windows) or `uv run --frozen --project packages/mp mp ...` from the `content-hub` root. Ensure `mp config --root-path` points to `content-hub` unless **both** `--src` and `--dst` are passed (see `mp-config` skill [SKILL.md](../mp-config/SKILL.md)).

## Exact Command Syntax

```bash
mp pack integration <INTEGRATION> [OPTIONS]
```

| Argument / Option | Shorthand | Behavior |
| :--- | :--- | :--- |
| `<INTEGRATION>` | | Integration folder name or identifier (required). |
| `--non-interactive` / `--interactive` | | `--interactive` is the default and opens a `questionary` TTY prompt when a TTY is attached. **Always pass `--non-interactive` in agent runs.** |
| `--src <DIR>` | | Existing source directory containing the integration. Defaults to searching configured `content/`. |
| `--dst <DIR>` | `-d` | Existing destination directory for `<identifier><YYYYMMDD>.zip`. Defaults to `<marketplace_path>/out/pack`. |
| `--beta <NAME>` | `-b` | Renames integration identifier and display name across definitions and scripts so it installs side-by-side as a beta package. |
| `--version <VER>` | `-v` | Historical integration version string (for example, `5.0`), located in Git history via `git log -S` and checked out in a temporary Git worktree when it differs from the current `pyproject.toml` version. |

## Agentic Workflow

1. **Prepare destination directory if using `--dst`**:
   `--dst` (`-d`) and `--src` enforce `exists=True, dir_okay=True, file_okay=False`. Run `mkdir -p <dst_dir>` before passing `--dst`.
   **Done when:** Custom `--dst` (if any) exists on disk.

2. **Run `mp pack integration` non-interactively**:
   ```bash
   mp pack integration <integration_name> --non-interactive
   ```
   - Side-by-side beta package without clobbering the installed official integration:
     ```bash
     mp pack integration <integration_name> --beta <IntegrationBetaName> --non-interactive
     ```
   - Historical integration version (pass the version number such as `5.0`, not a Git SHA):
     ```bash
     mp pack integration <integration_name> --version 5.0 --non-interactive
     ```
   **Done when:** Command exits `0`, logs `Successfully created integration zip: <path>.zip` (named `<identifier><YYYYMMDD>.zip`), and `test -f <path>.zip` succeeds.

## Key Gotchas

- **Always pass `--non-interactive`**: In pseudo-TTY agent shells (`is_tty() == True`), omitting `--non-interactive` launches an interactive `questionary` checkbox prompt that blocks execution indefinitely.
- **`-v` means `--version` (not `--verbose`), and takes a version number (not a Git SHA/tag)**: `mp pack` searches `git log -S` for `"integration_version: <VER>"` or `version = "<VER>"`; passing a commit SHA or branch name raises `BadParameter` and exits `1`. For verbose logs, place `-v` before `pack`: `mp -v pack integration <name> --non-interactive`.
