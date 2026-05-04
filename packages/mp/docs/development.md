# Development Guide

## Project Structure

The `mp` project follows this basic structure:

```
mp/
├── src/mp/         # Source code
│   ├── build_project/  # Integration building functionality
│   ├── check/      # Code checking functionality
│   ├── core/       # Core utilities and data models
│   ├── format/     # Code formatting functionality
│   └── __init__.py # Main entry point
├── tests/          # Test suite
├── docs/           # Documentation
└── pyproject.toml  # Project configuration
```

## Setting Up Development Environment

1. Clone the repository and install it in development mode:

```bash
git clone <repository-url>
cd mp
python -m virtualenv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -e ".[dev]"
```

2. Install pre-commit hooks (recommended):

```bash
pre-commit install
```

## Code Style and Quality

This project follows these standards:

- PEP 8 for code style
- Type hints on all functions and methods
- Docstrings in Google style format
- Ruff for linting and formatting
- MyPy for static type checking

You can automatically check and format your code using the tool itself:

```bash
# Format code
mp format

# Check code
mp check --static-type-check
```

## Logging

The `mp` tool uses an asynchronous logging setup with `QueueHandler` and a built-in `logging` module to ensure it works smoothly as a standalone CLI. 

To use the logger in your module:
1. Import `logging`: `import logging`
2. Create a logger using `__name__`: `logger = logging.getLogger(__name__)`
3. Use the logger instead of `print`, `rich.print`, or `typer.echo`. For example: `logger.info("...")`, `logger.error("...")`, etc.

The CLI supports global `--verbose` (`-v`) and `--quiet` (`-q`) flags to control output verbosity across all commands, similarly to `uv`. These are handled automatically by the root application callback and `RuntimeParams`.

## Testing

Run the test suite using pytest:

```bash
python -m pytest
```

For coverage information:

```bash
python -m pytest --cov=mp
```

## Creating New Commands

The project uses Typer for command-line interfaces. To add a new command:

1. Create a new package in `src/mp/` or add to an existing one
2. Define your command function with Typer decorators
3. Add your command to the main app in `src/mp/__init__.py`

Example:

```python
# In src/mp/my_command/__init__.py
import typer


app = typer.Typer()


@app.command(name="my-command")
def my_command() -> None:
    """My new command."""
    # Command implementation here
    ...


# Then in src/mp/__init__.py
from mp.my_command import app as my_command_app


# ...
main_app.add_typer(my_command_app, name="my-command")
```

## Data Models

The project uses abstract base classes and TypedDict for data models. Key classes
include:

- `Buildable`: Abstract base class for objects that can be serialized to and from
  different formats
- `BuildableScript`: Similar to `Buildable` but specifically for script components
- `ScriptMetadata`: For metadata associated with scripts
- `SequentialMetadata`: For metadata that appears in sequences

Extend these classes when adding new data models for integration components.

## Contributing

1. Create a feature branch from `main`
2. Make your changes
3. Run tests and ensure code quality
4. Submit a pull request

See [contributing.md](./contributing.md) for more details.
