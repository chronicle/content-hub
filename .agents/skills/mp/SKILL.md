---
name: mp
description: Orchestrates end-to-end Google SecOps Content Hub workflows with the mp CLI package - binary resolution, root-path setup, multi-step QA, packaging, and remote tenant sync. Use when working across multiple mp commands, onboarding to mp, or preparing an integration or playbook PR. Don't use for a single known mp subcommand (use the specific mp-<command> skill) or SIEM log parser validation.
---

# `mp` CLI Package Skill

`mp` (`wmp` on Windows, source in `packages/mp/`) is the CLI for developing, validating, testing, building, packaging, and syncing Google SecOps Content Hub content (response integrations, playbooks, Case/Alert views, custom fields, and alert grouping rules).

## 1. Resolve the `mp` Invocation Prefix

Pick one invocation prefix and use it consistently for the session:

1. **From the `content-hub` checkout root (preferred when `mp` is not on `PATH` or when testing local `packages/mp` edits)**:
   ```bash
   uv run --frozen --project packages/mp mp --version
   ```
   - If system Python 3.11 lacks SQLite support (`ModuleNotFoundError: No module named '_sqlite3'`), use `uv`'s managed Python 3.11:
     ```bash
     uv run --frozen --python-preference only-managed --project packages/mp mp --version
     ```
2. **Globally installed `mp`**:
   ```bash
   mp --version
   ```
   *(On Windows, replace `mp` with `wmp` to avoid PowerShell alias collisions.)*

**Done when:** `<mp> --version` exits `0` and prints `mp <version>`.

## 2. Verify Repository Root Configuration (`.mp_config`)

`mp` does **not** infer the Content Hub root from your current working directory. On a fresh machine, `.mp_config` (stored per-user, e.g. `~/.config/mp-cli-tool/.mp_config` on Linux) defaults `marketplace_path` to `~/marketplace`, causing `build`, `validate`, `test`, `pack`, `push`, and `pull` to look in the wrong directory until configured.

```bash
<mp> config --display-config
```

If `Marketplace path` does not match the active `content-hub` repository root:
- **Side-effect gate**: Because `.mp_config` is shared across the user's machine and git worktrees, confirm with the user before overwriting `--root-path` if it already points to another existing checkout.
- Update the root path:
  ```bash
  <mp> config --root-path /absolute/path/to/content-hub --display-config
  ```

**Done when:** `Marketplace path` in `--display-config` matches the target `content-hub` root directory.

## 3. Route to the Right Command Skill

Load the dedicated skill (`mp-<command>`) for any command you are about to run so its flag rules, exit-code traps, and side-effect gates are active:

| Command | Skill | Purpose |
| :--- | :--- | :--- |
| `mp config` | `mp-config` ([SKILL.md](../mp-config/SKILL.md)) | Configure `root-path`, worker `processes` (`1-10`), Gemini key, and concurrency. |
| `mp format` | `mp-format` ([SKILL.md](../mp-format/SKILL.md)) | Format Python files via `ruff format`. |
| `mp check` | `mp-check` ([SKILL.md](../mp-check/SKILL.md)) | Lint (`ruff check`) and static type-check (`ty check`) Python files. |
| `mp validate` | `mp-validate` ([SKILL.md](../mp-validate/SKILL.md)) | Run pre-build structural, schema, and release-hygiene validations. |
| `mp test` | `mp-test` ([SKILL.md](../mp-test/SKILL.md)) | Run per-integration `pytest` suites in isolated `.venv` environments. |
| `mp build` | `mp-build` ([SKILL.md](../mp-build/SKILL.md)) | Compile integrations, playbooks, or repositories into `out/`, or `--deconstruct`. |
| `mp pack` | `mp-pack` ([SKILL.md](../mp-pack/SKILL.md)) | Package an integration into `<identifier><YYYYMMDD>.zip` under `out/pack/`. |
| `mp login` | `mp-login` ([SKILL.md](../mp-login/SKILL.md)) | Authenticate to a Chronicle SecOps (GCP IAM/ADC) or legacy SOAR tenant. |
| `mp pull` | `mp-pull` ([SKILL.md](../mp-pull/SKILL.md)) | List or pull integrations, playbooks, views, custom fields, or grouping rules. |
| `mp push` | `mp-push` ([SKILL.md](../mp-push/SKILL.md)) | Validate, build, and upload content to a remote SecOps tenant. |
| `mp self update` | `mp-self` ([SKILL.md](../mp-self/SKILL.md)) | Upgrade a standalone `mp` installation from GitHub `main`. |

## 4. Standard Multi-Command Pipelines

### Integration Pre-PR Pipeline (Local Only)

Run in order from the repository root for `<integration_dir>` (with directory name `<integration_name>`):

1. **Sync lockfile & test venv if `pyproject.toml` changed**:
   `uv lock --project <integration_dir> && uv sync --dev --project <integration_dir>`
2. **Format**: `<mp> format <integration_dir>`
3. **Lint & Type-Check**: `<mp> check <integration_dir> --static-type-check --raise-error-on-violations --output-format concise`
4. **Validate Structure & Metadata** (`BROWSER=true` prevents opening a browser; once committed on a branch, include `GITHUB_PR_SHA=$(git rev-parse HEAD)` to enable version-bump checks against `origin/main`):
   `BROWSER=true GITHUB_PR_SHA=$(git rev-parse HEAD) <mp> validate integration <integration_name>`
5. **Run Unit Tests**: `BROWSER=true <mp> test --integration <integration_name>`
6. **Verify Build Compilation**: `<mp> build integration <integration_name>`

**Done when:** Every step exits `0`, logs confirm `<integration_name>` was actually processed (misspelled names exit `0` silently), `out/content/response_integrations/` contains the built `Integration-*.def`, and `git status` has no stray untracked files.

### Playbook Pre-PR Pipeline (Local Only)

1. `BROWSER=true GITHUB_PR_SHA=$(git rev-parse HEAD) <mp> validate playbook <playbook_name>`
2. `<mp> build playbook <playbook_name>`

**Done when:** Both commands exit `0` and `out/content/Playbooks/playbook_definitions/` contains the built playbook JSON.

## Global Agent & Sandbox Guardrails

- **Sandbox & network awareness**: Every `mp` invocation writes `[RUNTIME]` flags to `.mp_config`, runs a 2s background GitHub `main` version check, and posts sanitized command telemetry unless `report: false` is set in `~/.mp_cache/config.yaml` or CI env vars are active. Sandboxed agent runners (Codex CLI, Claude Code, Gemini CLI) need write access to `~/.config/mp-cli-tool/` (or custom `XDG_CONFIG_HOME`) and `~/.mp_cache/`.
- **Verbosity flags**: Subcommands that define their own `--verbose`/`--quiet` options (`check`, `format`, `build`, `validate`, `test`) overwrite root `mp -v`/`-q`; pass `--verbose` directly on the subcommand when debugging.
- **Working-tree cleanliness**: `out/`, `downloads/`, `.integrations_cache/`, and `.mp_cache/` are gitignored, whereas interrupted `<integration_dir>/.report.json` files are **not** gitignored. Ensure `git status` has no stray untracked artifacts before committing.
- **`packages/mp` CI gates**: Modifying `packages/mp/src/**` or `packages/mp/tests/**` triggers `package_version_check.yml` (`cd packages/mp && uv version --bump patch && uv lock --check`); any `packages/mp/**` change also runs `lint.yml` / `mp_code_check.yml` (`ruff check`, `ty check`, `pyrefly check`) and `test_mp.yml` (`pytest tests`).
