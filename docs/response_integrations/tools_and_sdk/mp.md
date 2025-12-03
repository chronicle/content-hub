# mp: Your Google SecOps Content Hub Powerhouse

**`mp`**, short for **`marketpalce`**, is a command-line interface (CLI)
tool designed to streamline the development and maintenance of Google SecOps Content Hub
response integrations.
It empowers developers by providing a unified platform for building,
testing, and ensuring the quality of their response integrations.

## Key Features

- **Build Response Integrations**: Convert non-built response integrations to the format required by
  Google SecOps Content Hub
- **Code Quality**: Format and lint Python code with ruff, and statically type-check
  with mypy
- **Developer Workflow**: Streamline the development process with helpful commands and
  fast dependency management using uv

## Documentation

For detailed information on how to use and contribute to `mp`, please refer to the
documentation:

- [The Main README](/packages/mp/README.md)
- [Installation Guide](/packages/mp/docs/installation.md)—How to install the tool
- [Usage Guide](/packages/mp/docs/usage.md)—How to use the available commands
- [Development Guide](/packages/mp/docs/development.md)—How to set up your development environment
- [Response Integrations Guide](/packages/mp/docs/response_integrations.md)—How to work with response
  integrations
- [Contributing Guidelines](/packages/mp/docs/contributing.md)—How to contribute to the project

## Quick Start

### Installation

From the repo's root directory run

```bash
pip install packages/mp
```

```bash
# Get help
mp --help

# Format Python files
mp format path/to/files

# Check code quality
mp check path/to/files --static-type-check --fix --unsafe-fixes

# Build an integration
mp build --quiet --repository third_party

# Run integration tests pre build
mp test --verbose --integration my_integration

# Configure mp parameters
mp config --root-path . --processes 7 --display-config
```

## Development Environment Commands

The `dev-env` subcommands help you interact with the development playground environment.

### Login to Dev Environment

Authenticate and verify credentials (default):

```bash
mp dev-env login
```

Skip credential verification:

```bash
mp dev-env login --no-verify
```

### Deploy an Integration to Dev Environment

Build and deploy an integration to the dev environment:

```bash
mp dev-env push <integration_name>
```

- `<integration_name>`: The name of the integration directory under `content/response_integrations/commercial` or
  `content/response_integrations/third_party`.
