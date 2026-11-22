---
name: mp-push
description: Validates, builds, and uploads integrations, playbooks, Case/Alert views, custom fields, and alert grouping rules to a remote SecOps environment. Use when deploying local Content Hub artifacts to a playground or staging tenant, or preflight-validating a view against a live server. Don't use for offline ZIP creation (use mp-pack) or downloading remote content (use mp-pull).
---

# `mp push` Skill

Builds and uploads local content to the remote SecOps tenant configured in `~/.mp_dev_env.json` (replaces deprecated `mp dev-env push` and `mp dev-env deploy`).

> **Invocation & Prerequisites**: Run `mp ...` (`wmp` on Windows) or `uv run --frozen --project packages/mp mp ...` from the `content-hub` root. Requires an active `~/.mp_dev_env.json` session (`mp-login` skill [SKILL.md](../mp-login/SKILL.md)) and `mp config --root-path` (`mp-config` skill [SKILL.md](../mp-config/SKILL.md)).

## Exact Subcommands & Flags

Pay close attention to source-path flag differences (`--src` vs `--custom` vs positional path):

```bash
mp push integration <INTEGRATION> [--src <DIR>] [--staging] [--custom] [--keep-zip]
mp push custom-integration-repository
mp push playbook <PLAYBOOK> [--src <DIR>] [--include-blocks] [--keep-zip]
mp push view [<VIEW_NAME_OR_ID>] [--custom <DIR>] [--validate] [--force] [--all]
mp push custom-field [<FIELD_NAME_OR_YAML_PATH>] [--scope <alert|case|alert,case|shared>] [--force] [--all]
mp push alert-grouping-rule [<RULE_NAME_OR_YAML_PATH>] [--force] [--all]
```

## Agentic Workflow

1. **Verify target tenant and preflight locally**:
   - Inspect non-secret fields (`auth_mode`, `project`, `location`, `instance`, `api_root`) in `~/.mp_dev_env.json` so you know which tenant will be modified (never print `api_key` or `password`).
   - For views, run the zero-upload preflight first:
     ```bash
     mp push view "<view_name_or_id>" --validate
     ```
     `--validate` checks all referenced custom fields, widgets, and integration dependencies against the live server without uploading. If it reports `[VALIDATION ERROR] Custom Field Not Installed`, push the required custom field(s) first (with `--force` if newly created).
   **Done when:** Target tenant is verified and preflight checks pass.

2. **Side-effect gate before any live upload**:
   Every `mp push` command without `--validate` mutates a live remote SecOps environment. Show the user the exact `mp push ...` command and target tenant identifier (`project`/`instance` or `api_root`), and highlight if `--force` (creates new views/widgets/fields/rules on server), `--all` (bulk push), or `custom-integration-repository` is included. Proceed only after explicit user confirmation.
   **Done when:** User explicitly approves the push.

3. **Execute `mp push` and verify post-push warnings**:
   Run the approved command. When pushing views, inspect logs for `[VALIDATION WARNING] Widget Not Persisted by Platform` (indicates the target tenant omitted a widget due to disabled feature flags or missing modules).
   **Done when:** Command exits `0` and logs upload confirmation without unexpected omissions.

## Key Gotchas

- **Creation is blocked without `--force`**: `mp push view`, `mp push custom-field`, and `mp push alert-grouping-rule` update existing server entities by default and exit `1` if the entity (or a view widget) does not yet exist on the server unless `--force` is passed.
- **No `--custom` flag on `custom-field` or `alert-grouping-rule`**: Unlike `mp pull`, `mp push custom-field` and `mp push alert-grouping-rule` do **not** accept `--custom` or `--src`. Pass an explicit `.yaml` file path as the positional argument to push a file outside `content/`.
- **Automatic dev minor-version bump**: `mp push integration` hashes `pyproject.toml` dependencies into `<marketplace_path>/.integrations_cache/version_cache.yaml` and increments the minor version inside the built `.def` so SOAR rebuilds the integration's remote virtual environment when dependencies change.
