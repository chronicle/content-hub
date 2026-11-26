# Development Guide

## Project Structure

The `packages/mp` package is organized by CLI domain under `src/mp/`:

```text
packages/mp/
├── src/mp/
│   ├── main.py                # CLI entry point (mounts all Typer sub-apps)
│   ├── build_project/         # Integration, playbook, view, and repository build/deconstruct flows
│   ├── check/                 # Ruff linting and ty static type checking command
│   ├── config/                # Persistent .mp_config CLI settings command
│   ├── core/                  # Config, constants, Pydantic/TypedDict data models, libcst, subprocess, Gemini SDK
│   ├── describe/              # Gemini AI description generation, evaluation, regression testing, and accept flows
│   ├── dev_env/               # SecOps login, push, and pull clients (Chronicle IAM/ADC and legacy SOAR API)
│   ├── format/                # Ruff formatting command
│   ├── pack/                  # SOAR-importable integration ZIP packaging and Git worktree checkout
│   ├── run_pre_build_tests/   # Parallel per-integration pytest runner and JSON report processor
│   ├── self_update/           # Self-upgrade command (mp self update)
│   ├── telemetry/             # Opt-out sanitized command usage telemetry
│   └── validate/              # Pre-build structural, metadata, and release-hygiene validators
├── tests/                     # Unit and property-based test suite (pytest + hypothesis)
├── docs/                      # Package and command documentation
├── pyproject.toml             # Package metadata and dependencies (Python >=3.11,<3.12)
├── ruff.toml                  # Ruff lint and format rules
├── ty.toml                    # Astral ty static type-checker configuration
└── pyrefly.toml               # Pyrefly type-checker configuration
```

## Setting Up the Development Environment

From the `content-hub` repository root:

```bash
cd packages/mp
uv sync --dev
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

## Code Style and Quality Checks

CI enforces the following checks on every change touching `packages/mp/` (see `.github/workflows/lint.yml` and `.github/workflows/mp_code_check.yml`):

```bash
# Run from packages/mp/ with .venv activated
ruff check --output-format grouped
ty check --output-format concise
pyrefly check --min-severity info
```

Format and lint only your modified files via `mp` (avoid running `ruff format .` across untouched files so pull requests remain free of unrelated reformat hunks):

```bash
mp format <modified_files>
mp check src tests --static-type-check --raise-error-on-violations
```

### Package Version & Lockfile Gate

When a pull request modifies files under `packages/mp/src/` or `packages/mp/tests/`, `.github/workflows/package_version_check.yml` requires bumping the `version` in `packages/mp/pyproject.toml` and keeping `packages/mp/uv.lock` synchronized:

```bash
cd packages/mp
uv version --bump patch
uv lock --check
```

## Logging

`mp` uses an asynchronous logging setup with `QueueHandler` and Python's standard `logging` module:

1. Import `logging` and instantiate a module logger: `logger: logging.Logger = logging.getLogger(__name__)`.
2. Emit output via `logger.info(...)`, `logger.warning(...)`, `logger.error(...)`, or `logger.exception(...)` rather than `print` or `rich.print`.
3. Respect `--verbose` (`-v`) and `--quiet` (`-q`), which are wired through `mp.core.config.RuntimeParams`.

## Running Unit Tests

Run the `packages/mp` unit test suite from `packages/mp/`:

```bash
pytest tests -n auto --cov
```

## Creating New Commands

`mp` uses [Typer](https://typer.tiangolo.com/). To add a new top-level command:

1. Create a subpackage under `src/mp/<command_module>/` with a `typer_app.py` defining a `typer.Typer` instance.
2. Decorate command functions with `@track_command` from `mp.telemetry` when appropriate.
3. Register the sub-application in `src/mp/main.py` inside `main()`:

```python
# In src/mp/my_command/typer_app.py
from __future__ import annotations

import typer

my_command_app: typer.Typer = typer.Typer(name="my-command", help="Describe what my-command does.")


@my_command_app.command(name="run")
def run_command() -> None:
    """Execute the command."""


# In src/mp/main.py
from .my_command.typer_app import my_command_app

# Inside main():
app.add_typer(my_command_app, name="my-command")
```

4. Add unit tests under `packages/mp/tests/test_mp/` and command documentation under `packages/mp/docs/commands/`.

## Data Models

Core content schemas live under `src/mp/core/data_models/` and build on base abstractions in `src/mp/core/data_models/abc.py`:

- `Buildable`: Abstract base class for models converting between non-built (YAML/source) and built (JSON/SOAR) representations.
- `BuildableComponent`: Base class for integration components backed by code and metadata.
- `SingularComponentMetadata` / `ComponentMetadata` / `SequentialMetadata`: Structured Pydantic metadata models for single and sequential definitions.

## Contributing

See [contributing.md](./contributing.md) for pull request guidelines and CLA requirements.
