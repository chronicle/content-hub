# mp: Google SecOps Marketplace CLI

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](./LICENSE)
[![Python Version](https://img.shields.io/badge/Python-3.11-blue.svg)](https://www.python.org/downloads/)
![Maintenance](https://img.shields.io/maintenance/yes/2026)

**`mp`**, short for **`marketplace`**, is the official command-line interface (CLI) for developing, validating, testing, packaging, and deploying Google SecOps Content Hub integrations, playbooks, views, custom fields, and alert grouping rules.

## Quick Start

### 1. Install as a persistent tool (Recommended)

Install `mp` once and use it everywhere (requires Python `>=3.11,<3.12` and `uv`):

```bash
# Install from the main branch
uv tool install --python 3.11 mp --from git+https://github.com/chronicle/content-hub.git#subdirectory=packages/mp

# Point mp at your local content-hub checkout
mp config --root-path /path/to/content-hub

# Inspect available commands
mp --help
```

### 2. Run from a local `content-hub` checkout

Run directly against the workspace version without global installation:

```bash
uv run --project packages/mp mp --help
```

### 3. One-time usage without a checkout

```bash
uvx --python 3.11 --from git+https://github.com/chronicle/content-hub.git#subdirectory=packages/mp mp --help
```

For full setup details, see the [Installation Guide](docs/installation.md).

> [!NOTE]
> **Windows Users**: Use `wmp` instead of `mp` for all commands to avoid conflicts with default PowerShell system aliases.

## Key Capabilities

- **Build and Package**: Compile non-built YAML and Python source into deployable SOAR artifacts (`build`), deconstruct built packages back to source (`build ... --deconstruct`), or generate SOAR-importable ZIP archives (`pack`).
- **Quality Assurance**: Format Python code (`format`), run `ruff` linting and `ty` static type checks (`check`), validate repository schemas and release hygiene (`validate`), and execute per-integration `pytest` suites (`test`).
- **Environment Sync**: Authenticate (`login`), pull (`pull`), and push (`push`) integrations, playbooks, Case/Alert views, custom fields, and alert grouping rules against a SecOps tenant.

## Command Reference

| Command | Description | Documentation |
| :--- | :--- | :--- |
| `build` | Build or deconstruct integrations, playbooks, or full repositories. | [Docs](docs/commands/build.md) |
| `check` | Lint (`ruff`) and optionally type-check (`ty`) Python code. | [Docs](docs/commands/check.md) |
| `config` | Configure `mp` settings. | [Docs](docs/commands/config.md) |
| `describe` | Generate AI descriptions for integration actions. | [Docs](docs/commands/describe.md) |
| `format` | Format Python files using `ruff format`. | [Docs](docs/commands/format.md) |
| `login` | Authenticate to a Chronicle SecOps or legacy SOAR environment. | [Docs](docs/commands/dev_env.md#login) |
| `pack` | Package an integration into a SOAR-supported ZIP file. | [Docs](docs/commands/pack.md) |
| `pull` | Pull integrations, playbooks, views, custom fields, or grouping rules. | [Docs](docs/commands/dev_env.md) |
| `push` | Build and push content to a SecOps environment. | [Docs](docs/commands/dev_env.md) |
| `self` | Update the `mp` CLI tool (`mp self update`). | [Docs](docs/commands/self.md) |
| `test` | Run pre-build integration `pytest` suites. | [Docs](docs/commands/test.md) |
| `validate` | Validate integration and playbook structure, schemas, and metadata. | [Docs](docs/commands/validate.md) |

*(Note: `mp dev-env` is deprecated; use `mp login`, `mp push`, and `mp pull` directly.)*

## AI Agent Skills

This repository includes [Agent Skills](https://agentskills.io) for the `mp` package (`mp`) and each core CLI command (`mp-build`, `mp-check`, `mp-config`, `mp-format`, `mp-login`, `mp-pack`, `mp-pull`, `mp-push`, `mp-self`, `mp-test`, `mp-validate`):

- **Google Gemini (`Gemini CLI`, `Antigravity`)**: Auto-discovered from [`.agents/skills/`](../../.agents/skills/).
- **OpenAI (`Codex CLI`, `Codex`)**: Auto-discovered from [`.agents/skills/`](../../.agents/skills/).
- **Anthropic (`Claude Code`)**: Auto-discovered from [`.claude/skills/`](../../.claude/skills/) (linked to `.agents/skills/`). On Windows, ensure Git symlinks are enabled (`git config core.symlinks true`) before checkout.

## Documentation

- [Installation Guide](docs/installation.md)
- [Usage Guide](docs/usage.md)
- [Response Integrations Guide](docs/response_integrations.md)
- [Development Guide](docs/development.md)
- [Contributing Guidelines](docs/contributing.md)
- [Code of Conduct](docs/code-of-conduct.md)

## License

This project is licensed under the Apache License 2.0. See the [LICENSE](./LICENSE) file for details.
