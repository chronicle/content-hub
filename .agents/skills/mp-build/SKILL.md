---
name: mp-build
description: Compiles non-built Content Hub integrations, playbooks, or repositories into deployable SOAR artifacts under out/, or deconstructs built packages back into source layout. Use when verifying an integration or playbook compiles cleanly, building a repository index, or deconstructing built SOAR artifacts. Don't use for standalone importable ZIP archives (use mp-pack) or direct tenant uploads (use mp-push).
---

# `mp build` Skill

Transforms non-built YAML and Python source into SOAR platform artifacts under `<marketplace_path>/out/content/` (rewriting imports with `libcst` and downloading binary `.whl` dependencies), or reverses built artifacts back into non-built source with `--deconstruct`.

> **Invocation & Prerequisite**: Run `mp ...` (`wmp` on Windows) or `uv run --frozen --project packages/mp mp ...` from the `content-hub` root, and ensure `mp config --display-config` points `Marketplace path` to `content-hub` (see `mp-config` skill [SKILL.md](../mp-config/SKILL.md)).

## Exact Command Syntax

Use the subcommands (`integration`, `playbook`, `repository`); flag-based `mp build -i/-p/-r` is deprecated.

```bash
mp build integration <INTEGRATION_NAMES>... [--src <DIR>] [--dst <DIR>] [--deconstruct|-d] [--custom-integration] [--quiet|-q] [--verbose|-v]
mp build playbook <PLAYBOOK_NAMES>... [--src <DIR>] [--dst <DIR>] [--deconstruct|-d] [--quiet|-q] [--verbose|-v]
mp build repository <google|third_party|custom|playbooks|all_content>... [--quiet|-q] [--verbose|-v]
```

## Agentic Workflow

1. **Create custom `--dst` directories beforehand**:
   Typer validates `--src` and `--dst` with `exists=True, dir_okay=True, file_okay=False` on `mp build integration` and `mp build playbook`. If passing `--dst`, run `mkdir -p <dst_dir>` first.
   **Done when:** Any custom `--src` and `--dst` directories exist on disk.

2. **Execute the build or deconstruction**:
   - **Standard integration build** (writes to `out/content/response_integrations/<repo>/<identifier>/`):
     ```bash
     mp build integration <integration_name>
     ```
   - **Standard playbook build** (writes to `out/content/Playbooks/playbook_definitions/`):
     ```bash
     mp build playbook <playbook_name>
     ```
   - **Deconstruct a built integration or playbook back to source**:
     ```bash
     mkdir -p <dst_dir>
     mp build integration <integration_name> --deconstruct --src <built_parent_dir> --dst <dst_dir>
     ```
   - **Full repository build** (writes per-repo `marketplace.json` / `playbooks.json`, and checks duplicate integration identifiers when both `google` and `third_party` are built together):
     ```bash
     mp build repository google third_party
     ```
   **Done when:** Command exits `0` **and** you verify the compiled artifact (`Integration-*.def` under `out/content/response_integrations/` or `<playbook>.json` under `out/content/Playbooks/playbook_definitions/`, or `<dst_dir>`) exists on disk.

## Key Gotchas

- **Misspelled names still exit `0` (and valid builds log one `"could not be found"` line)**: `mp build integration <name>` searches `google` then `third_party`. For a valid integration in `google`, it builds in `google` and logs `"could not be found in the third_party marketplace"` (harmless); if misspelled, it logs `"could not be found"` in **both** and prints the reconfigure hint while still exiting `0`! Always verify `"Building the following integrations"` appeared and the `out/` artifact exists.
- **Incompatible flag combinations**: `--custom-integration` cannot be combined with `--deconstruct`, `--src`, or `--dst` (raises `typer.BadParameter`).
- **Binary-only wheel downloads**: Building an integration runs `uv export` then `pip download --only-binary=:all:` (`manylinux` on Linux, `win_amd64` on Windows). If a dependency only publishes an sdist on PyPI, pin its tarball URL via `uv add --project <integration_dir> "<pkg> @ <pypi_tarball_url>"`.
- **Suffixed integration aliases**: Passing `http` or `twilio` resolves `http_integration` / `twilio_integration`; for all others pass the exact folder name.
