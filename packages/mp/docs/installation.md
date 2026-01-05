# Installation Guide

## Prerequisites

- Python 3.11 or later (Python 3.11.0+ is officially supported)
- uv package manager

## Installation Steps

### 1. Install `uv`

Install uv in your base Python interpreter:

```bash
pip install uv
```

### 2. Clone the Repository

```shell
git clone <repository-url>
cd packages/mp
```

### 3. Set Up Project with `uv`

#### Development Installation

For development purposes, create a virtual environment and install dependencies in one
step:

```shell
uv sync --dev
```

This command creates a virtual environment in `.venv` directory and installs all
dependencies including development ones.

#### User Installation

For regular usage without development dependencies:

```shell
uv sync
```

### 4. Activate the Virtual Environment

```shell
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

### 5. Verify Installation

Verify that the installation was successful by running:

```bash
mp --help
```

You should see the help menu displaying the available commands.

> [!NOTE]
> **Windows Users**: if you are running on Windows, please use `wmp` instead of `mp` (e.g., `wmp --help`).

### Alternative: Direct Installation

You can also install the package directly to your base Python interpreter:

```shell
uv pip install .
# Or for development installation
uv pip install -e .
```

## Configure `mp`

When installing `mp` it automatically assumes the marketplace repo is installed at
`~/marketplace`.
To configure a different path run

```shell
mp config --root-path /path/to/marketplace 
```

To find more about configurations, run

```shell
mp config --help
```

## IDE Configuration
To run or debug the application from within an IDE, please make sure to set the project's Python interpreter to the executable located within the virtual environment created by uv. the relative path from packages/mp is:

- Windows: .venv\Scripts\python.exe

- macOS/Linux: .venv/bin/python

This ensures that the IDE can correctly utilize any shared run/debug configurations.

## Dependencies

If you need to update dependencies or re-sync your virtual environment:

```shell
uv sync
```

For development, also sync the dev-dependencies


```shell
uv sync --dev
```
