# mp: The Google SecOps Content Hub CLI

**`mp`**, short for **`marketplace`**, is a command-line interface (CLI) tool designed to streamline
the development and maintenance of content for the Google SecOps Content Hub. It provides a unified
set of commands for building, deconstructing, testing, and validating response integrations and
playbooks.

## Key Features

- **Build Content**: Package response integrations and playbooks into the format required by the
  Google SecOps platform.
- **Deconstruct Content**: Convert integrations and playbooks exported from Google SecOps back into
  the source-controlled, human-readable format used in this repository.
- **Validation & Testing**: Run validation checks and integration tests to ensure content quality
  and correctness.
- **Code Quality**: Format, lint, and statically type-check Python code using `ruff` and `mypy`.
- **Developer Workflow**: Simplify the development lifecycle with fast dependency management via
  `uv` and commands for interacting with a development environment.

## Installation

From the repository's root directory, run:

```bash
pip install packages/mp
```

## Usage

### General Help

To see a full list of commands and options, run:

```bash
mp --help
```

### Building Individual Content

To build a single integration or playbook, use the `build` command.

```bash
# Build a single integration
mp build --integration my_integration

# Build a single playbook
mp build --playbook my_playbook
```

### Deconstructing Content

The `deconstruct` process converts a single content item exported from Google SecOps into the more
readable and developer-friendly format used in this repository.

1. Place the exported content (e.g., `my_new_playbook.json`) into the appropriate directory (e.g.,
   `content/playbooks/third_party/community/`).
2. Run the `build` command with the `--deconstruct` flag.

```bash
# Deconstruct a playbook
mp build --playbook my_new_playbook --deconstruct

# Deconstruct an integration
mp build --integration my_new_integration --deconstruct
```

**Note:** The `deconstruct` command operates on a single content item by name and cannot be run on
an entire repository at once.

### Validating Individual Content

The `validate` command checks a specific content item for errors.

```bash
# Validate a single integration
mp validate --integration my_integration --only-pre-build
```

### Testing Individual Integrations

Run integration tests for a specific integration.

```bash
mp test --integration my_integration --verbose
```

## Repository-Level Commands

You can run `build`, `validate`, and `test` on entire repositories using the `--repository` flag.

The available repositories are:

- `google`: Response integrations developed by Google teams.
- `third_party`: Response integrations developed by partners or the community.
- `playbook`: All playbooks in the repository.

### Build or Validate a Repository

The `build` and `validate` commands work with all repository types.

```bash
# Build all third-party integrations
mp build --repository third_party

# Validate all playbooks
mp validate --repository playbook --only-pre-build
```

### Test a Repository

The `test` command can only be used with the `google` and `third_party` integration repositories.

```bash
# Test all Google-developed integrations
mp test --repository google
```

### Command Flags

You can use the following shorthand flags:

- `--repository` -> `-r`
- `--integration` -> `-i`
- `--playbook` -> `-p`

## Development Environment (`dev-env`)

The `dev-env` subcommands help you interact with a development playground environment.

### Login

Authenticate and verify your credentials.

```bash
mp dev-env login
```

### Push an Integration

Build and deploy an integration to the development environment.

```bash
mp dev-env push my_integration
```

- `my_integration`: The name of the integration directory. `mp` will find it in the project.

## Further Documentation

For more detailed information, please refer to the documentation within the `packages/mp` directory:

- [README](/packages/mp/README.md)
- [Installation Guide](/packages/mp/docs/installation.md)
- [Usage Guide](/packages/mp/docs/usage.md)
- [Development Guide](/packages/mp/docs/development.md)
- [Response Integrations Guide](/packages/mp/docs/response_integrations.md)
- [Contributing Guidelines](/packages/mp/docs/contributing.md)
