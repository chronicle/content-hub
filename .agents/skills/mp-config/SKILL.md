---
name: mp-config
description: Reads and updates persistent mp CLI configuration (.mp_config) including the content-hub root path, worker parallelism, Gemini API key, and Gemini concurrency. Use when configuring mp, fixing 'integrations could not be found' path errors, or checking active mp settings. Don't use for SecOps tenant authentication (use mp-login).
---

# `mp config` Skill

Manages persistent settings in `.mp_config` inside the platform user config directory (for example, `~/.config/mp-cli-tool/.mp_config` on Linux).

> **Invocation**: Run `mp ...` if installed on `PATH` (`wmp` on Windows), or `uv run --frozen --project packages/mp mp ...` from the `content-hub` repository root (see `mp` skill [SKILL.md](../mp/SKILL.md)).

## Exact Command Syntax

```bash
mp config [OPTIONS]
```

| Option | Validation / Constraints | Default in `.mp_config` |
| :--- | :--- | :--- |
| `--root-path <DIR>` | Must exist on disk and be a directory (`FileNotFoundError` / `NotADirectoryError` otherwise). | `~/marketplace` |
| `--processes <INT>` | Integer between `1` and `10` inclusive (`ValueError` outside `1..10`). | `5` |
| `--gemini-api-key <STR>` | Stored in `.mp_config`; takes priority over the `GEMINI_API_KEY` env var. | Unset |
| `--gemini-concurrency <INT>` | Integer `>= 1`. | `5` |
| `--display-config` | Prints `Marketplace path`, `Number of processes`, `Gemini concurrency`, and masked API key (`<first4>***`). | `False` |

## Agentic Workflow

1. **Inspect before mutating**:
   ```bash
   mp config --display-config
   ```
   **Done when:** Current `Marketplace path`, worker count, and Gemini key source are visible in output.

2. **Apply targeted configuration updates**:
   - **Side-effect gate**: `.mp_config` is global to the user account across shells and git worktrees. If `Marketplace path` already points to another existing checkout or a Gemini key is already saved, confirm with the user before overwriting it.
   - Point `mp` at the active `content-hub` workspace root:
     ```bash
     mp config --root-path /absolute/path/to/content-hub --display-config
     ```
   - Tune worker threads (`1` to `10`):
     ```bash
     mp config --processes 8 --display-config
     ```
   - **Secret hygiene for Gemini keys**: Prefer setting `GEMINI_API_KEY` in the user's shell environment rather than passing raw secret literals on the command line (which records them in agent transcripts and shell history). If persisting to `.mp_config` is requested, expand from an env var (`mp config --gemini-api-key "$GEMINI_API_KEY"`) or ask the user to run the command directly.
   **Done when:** `mp config --display-config` reflects the updated values and exits `0`.

## Key Gotchas

- **Silent no-op without flags**: Running bare `mp config` with no options exits `0` and prints nothing; include `--display-config` whenever you want confirmation output.
- **API key precedence**: A key saved in `.mp_config` overrides `GEMINI_API_KEY` in the shell environment (`--display-config` warns when both are set to different values and reveals the first 4 characters).
- **Separate from `mp login`**: `.mp_config` only stores local build/Gemini settings. Remote SecOps tenant credentials live in `~/.mp_dev_env.json` via `mp-login` ([SKILL.md](../mp-login/SKILL.md)).
