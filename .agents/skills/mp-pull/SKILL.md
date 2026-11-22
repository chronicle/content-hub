---
name: mp-pull
description: Lists or downloads and deconstructs integrations, playbooks, Case/Alert views, custom fields, and alert grouping rules from a remote SecOps environment. Use when inspecting installed remote tenant entities or pulling remote content into local YAML and Python files. Don't use for uploading local changes to a tenant (use mp-push) or authenticating (use mp-login).
---

# `mp pull` Skill

Downloads and deconstructs content from the SecOps tenant configured in `~/.mp_dev_env.json` (replaces deprecated `mp dev-env pull`).

> **Invocation & Prerequisites**: Run `mp ...` (`wmp` on Windows) or `uv run --frozen --project packages/mp mp ...` from the `content-hub` root. Requires an active `~/.mp_dev_env.json` session (`mp-login` skill [SKILL.md](../mp-login/SKILL.md)) and `mp config --root-path` (`mp-config` skill [SKILL.md](../mp-config/SKILL.md)).

## Exact Subcommands & Flags

Notice the destination option name differs between `integration`/`playbook` (`--dst`) and `view`/`custom-field`/`alert-grouping-rule` (`--custom`):

```bash
# Writes to <marketplace_path>/downloads/ by default (gitignored; does not overwrite content/)
mp pull integration <INTEGRATION> [--dst <DIR>] [--keep-zip]
mp pull playbook <PLAYBOOK> [--dst <DIR>] [--include-blocks] [--keep-zip]

# Read-only remote listing (zero local file writes)
mp pull view --list
mp pull custom-field --list [--scope <alert|case|alert,case|shared>]
mp pull alert-grouping-rule --list

# Writes directly into content/{views,custom_fields,alert_grouping_rules}/ by default (overwrites matching local files!)
mp pull view [<VIEW_NAME_OR_ID>] [--all] [--custom <DIR>]
mp pull custom-field [<FIELD_NAME_OR_ID_OR_FILE>] [--all] [--scope <SCOPE>] [--custom <FILE_OR_DIR>]
mp pull alert-grouping-rule [<RULE_CATEGORY_OR_ID_OR_FILE>] [--all] [--custom <FILE_OR_DIR>]
```

## Agentic Workflow

1. **Discover remote names/IDs first with `--list` (for views, custom fields, and grouping rules)**:
   `--list` is read-only and avoids guessing display names, scopes, or categories:
   ```bash
   mp pull view --list
   mp pull custom-field --list
   mp pull alert-grouping-rule --list
   ```
   **Done when:** Exact remote entity identifier, display name, or category is confirmed.

2. **Check for uncommitted local overwrites (Side-effect gate)**:
   - `mp pull integration` and `mp pull playbook` default to `downloads/` (gitignored) unless `--dst` points into `content/`.
   - `mp pull view`, `mp pull custom-field`, and `mp pull alert-grouping-rule` match existing files under `content/` (including renamed files matching `identifier`, `displayName` + `scopes`, or `category` + `categoryDetails`) and **overwrite them in place**. Moreover, `mp pull view` **automatically pulls and overwrites** dependent custom fields and alert grouping rules into `content/` even when `--custom` is passed for the view itself!
   - Inspect `git status --short content/` first. Confirm with the user before running any `pull` that could overwrite uncommitted local `content/` edits.
   **Done when:** Target local paths are clean or approved by the user.

3. **Execute `mp pull` and verify output files**:
   Run the targeted `mp pull <subcommand> ...` command and inspect the deconstructed directory or YAML file (`id` and `name` server fields are stripped automatically on custom fields and grouping rules).
   **Done when:** Command exits `0` and target local files exist on disk.

## Key Gotchas

- **`--dst` vs `--custom`**: Passing `--dst` to `mp pull view|custom-field|alert-grouping-rule` or `--custom` to `mp pull integration|playbook` fails with `No such option`.
- **`--custom` incompatible with `mp pull view --all`**: `mp pull view --all --custom <dir>` exits `1` by design; omit `--custom` when pulling `--all` views.
- **Scope filter semantics on `custom-field`**: `--scope alert,case` is an **OR** filter (matches alert-only, case-only, or shared), whereas `--scope shared` is an **AND** filter requiring both `alert` and `case` scopes.
