# Usage Guide

**`mp`**, short for **`marketplace`**, is a command-line interface (CLI) tool designed to streamline
the development and maintenance of content for the Google SecOps Content Hub. It provides a unified
set of commands for building, deconstructing, testing, and validating response integrations and
playbooks.

The commands can be run using the following:

- `mp` – primary command-line interface.
- `wmp` – alternative alias to avoid default alias conflicts that may appear (on Windows only).

## Installation

From the repository's root directory, run:

```bash
pip install packages/mp
```

## General Help

To see a full list of commands and options, run:

```bash
mp --help
```

To get help for a specific command:

```bash
mp <command> --help
```

## Building Content

To build a single integration or playbook, use the `build` command.

```bash
# Build a single integration
mp build --integration my_integration

# Build a single playbook
mp build --playbook my_playbook
```

You can use the following shorthand flags:

- `--integration` -> `-i`
- `--playbook` -> `-p`

## Deconstructing Content

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

You can use the following shorthand flags:

- `--deconstruct` -> `-d`

**Note:** The `deconstruct` command operates on a single content item by name and cannot be run on
an entire repository at once.

## Validating Content

The `validate` command checks a specific content item for errors.

```bash
# Validate a single integration
mp validate --integration my_integration --only-pre-build

# Validate a single playbook
mp validate --playbook my_playbook --only-pre-build
```

Additional options:

- `--only-pre-build`: Run only pre-build validation checks, skipping the full build process
- `--quiet`: Reduce output verbosity
- `--verbose`: Increase output verbosity

## Testing Integrations

Run integration tests for a specific integration.

```bash
mp test --integration my_integration --verbose
```

## Repository-Level Commands

You can run `build`, `validate`, and `test` on entire repositories using the `--repository` or `-r`
flag.

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
mp dev-env push integration <integration_name>
```

- `<integration_name>`: The name of the integration directory. `mp` will find it in the project.

Options:

- `--staging`: push integration to staging environment.

## Code Quality Commands

### Format Code

To format Python files in your project:

```bash
mp format [FILE_PATHS...]
```

Options:

- `--changed-files`: Format only files changed in Git
- `--quiet`: Reduce output verbosity
- `--verbose`: Increase output verbosity

### Lint and Check Code

To lint and check Python files:

```bash
mp check [FILE_PATHS...]
```

Options:

- `--fix`: Automatically fix minor issues
- `--changed-files`: Check only files changed in Git
- `--static-type-check`: Run static type checking with mypy
- `--raise-error-on-violations`: Raise error if violations are found
- `--quiet`: Reduce output verbosity
- `--verbose`: Increase output verbosity
