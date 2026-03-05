# mp: Your Google SecOps Marketplace Integration Powerhouse

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](./LICENSE)
[![Python Version](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/downloads/)
![Maintenance](https://img.shields.io/maintenance/yes/2026)

**`mp`**, short for **`marketplace`
**, is the official command-line interface (CLI) for developing, maintaining, and deploying Google SecOps marketplace integrations. It streamlines the entire lifecycle from coding to deployment.

## Workflow

The `mp` tool sits at the center of your integration development workflow:

> [!NOTE]
> **Windows Users**: Please use `wmp` instead of
`mp` for all commands to avoid conflicts with system aliases.

## Key Features

- **Build & Package**: transforming source code into deployable artifacts.
- **Quality Assurance**: Automated linting (`check`), formatting (`format`), and testing (`test`).
- **Development Loop**: Rapidly push changes to your development environment (`dev-env`).

## Command Reference

| Command    | Description                                             | Documentation                     |
|:-----------|:--------------------------------------------------------|:----------------------------------|
| `build`    | Build integrations or playbooks into deployable format. | [Docs](docs/commands/build.md)    |
| `check`    | Lint and sanity-check your code.                        | [Docs](docs/commands/check.md)    |
| `config`   | Configure `mp` settings.                                | [Docs](docs/commands/config.md)   |
| `describe` | Generate AI descriptions for integration actions.       | [Docs](docs/commands/describe.md) |
| `format`   | Auto-format Python files.                               | [Docs](docs/commands/format.md)   |
| `test`     | Run pre-build integration tests.                        | [Docs](docs/commands/test.md)     |
| `validate` | Validate integration structure and metadata.            | [Docs](docs/commands/validate.md) |
| `dev-env`  | Interact with dev environment (login, push).            | [Docs](docs/commands/dev_env.md)  |

## Documentation

For comprehensive guides on how to contribute:

- [Installation Guide](docs/installation.md)
- [Usage Guide](docs/usage.md)
- [Development Guide](docs/development.md)
- [Marketplace Integration Guide](docs/marketplace.md)
- [Contributing Guidelines](docs/contributing.md)

## License

This project is licensed under the Apache License 2.0—see the [LICENSE](./LICENSE) file for details.