# Marketplace CLI (mp) - Agent Guide

The `mp` CLI is the central orchestration tool for the Google SecOps Marketplace development lifecycle. It manages the transformation between raw source code and deployable platform artifacts.

## Core Capabilities & Lifecycle

### 1. Project Scaffolding & Transformation (`build`)
The `build` command is the bridge between the Content Hub and the Google SecOps SOAR platform.
- **Build**: Transforms modular source code (actions, connectors, jobs) into a single deployable `.zip` artifact.
- **Deconstruct (`-d`)**: Reverse-engineers a built integration artifact back into the modular hub structure, enabling legacy content to be brought into the modern development workflow.
- **Scopes**: Operates on individual `integration`, `playbook`, or entire `repository` sets (`google`, `third_party`).

### 2. Quality Assurance & Standards (`check`, `validate`, `format`)
Ensures all content meets rigorous security and architectural standards.
- **`check`**: Deep linting (using Ruff) with a focus on SecOps-specific patterns. Supports `--fix` for auto-remediation and `--static-type-check` (using Mypy) for robust typing.
- **`validate`**: Structural verification. It checks for:
    - Missing required files (e.g., icons, `README.md`).
    - Valid JSON/YAML metadata schemas.
    - Correct implementation of mandatory SDK methods.
- **`format`**: Standardizes code formatting across the repository.

### 3. Automated Documentation (`describe`)
Leverages Gemini AI to analyze Python action scripts and automatically generate:
- Action descriptions.
- Parameter explanations.
- Capability summaries.
This ensures consistent and high-quality documentation for end-users.

### 4. Development Loop & Integration (`dev-env`)
Facilitates rapid iteration by connecting local development to live SecOps tenants.
- **`login`**: Securely stores API credentials (API Root, Key/Username) for the target environment.
- **`push`**: Directly uploads and installs a local integration or playbook into a development tenant for real-time testing.
- **`pull`**: Downloads content from a live tenant and deconstructs it into the local workspace.

### 5. Testing (`test`)
Executes pre-build tests ensuring that integrations behave correctly before they are even packaged.

## Technical Architecture

The CLI is structured as a modular Python package:
- **`src/mp/main.py`**: Entry point and command routing.
- **`src/mp/core/`**: Internal SDK containing shared logic for path mapping, data models, and platform communication.
- **`src/mp/[command]/`**: Each major command is isolated in its own submodule, containing its specific business logic and CLI interface definitions.

## Usage for Agents
When working on integrations or playbooks:
1. **Research**: Use `mp build --deconstruct` to understand legacy artifacts.
2. **Implementation**: Use `mp format` and `mp check --fix` frequently during development.
3. **Verification**: Always run `mp validate` before proposing changes.
4. **Deployment**: Use `mp dev-env push` to verify behavioral correctness in a live environment.

### Standard Execution
The standard way to run any `mp` command is to `cd` into the `packages/mp` directory and use the `mp` executable from its internal virtual environment:
```bash
cd packages/mp
.venv/bin/mp [command]
```
Avoid using a global `mp` installation if available, as the internal venv ensures all dependencies (like `libcst`, `typer`, etc.) are correctly versioned for this repository.
