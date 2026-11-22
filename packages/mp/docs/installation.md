# Installation Guide

## Prerequisites

- Python `3.11.x` (`requires-python = ">=3.11,<3.12"` in `pyproject.toml`) with `sqlite3` support.
- [uv](https://docs.astral.sh/uv/) package manager.

> [!TIP]
> If your system Python 3.11 was built without SQLite headers (`ModuleNotFoundError: No module named '_sqlite3'`), install a `uv`-managed Python 3.11 (`uv python install 3.11`) and pass `--python-preference only-managed` to `uv` commands.

## Installation Options

### Option 1: Persistent Tool Installation (Recommended)

Install `mp` once and keep it on your `PATH`:

```bash
uv tool install --python 3.11 mp --from git+https://github.com/chronicle/content-hub.git#subdirectory=packages/mp
```

Verify the installation:

```bash
mp --version
mp --help
```

To upgrade `mp` later, run either:

```bash
uv tool upgrade mp
# or
mp self update
```

### Option 2: Run Directly from a Local `content-hub` Checkout

If you already have `content-hub` cloned locally, you can run `mp` directly from `packages/mp` without installing it globally:

```bash
uv run --project packages/mp mp --help
```

### Option 3: One-Time Usage Without Cloning

```bash
uvx --python 3.11 --from git+https://github.com/chronicle/content-hub.git#subdirectory=packages/mp mp --help
```

### Option 4: Local Development Environment (`packages/mp`)

Use this setup when developing or testing changes to `mp` itself.

#### 1. Clone the Repository

```bash
git clone https://github.com/chronicle/content-hub.git
cd content-hub/packages/mp
```

#### 2. Sync the Virtual Environment with `uv`

For development (includes `pytest`, `hypothesis`, `pyrefly`, and type stubs):

```bash
uv sync --dev
```

For runtime dependencies only (excluding the `dev` dependency group):

```bash
uv sync --no-dev
```

#### 3. Activate the Virtual Environment

```bash
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

#### 4. Verify Installation

```bash
mp --help
```

> [!NOTE]
> **Windows Users**: On Windows, run `wmp` instead of `mp` (for example, `wmp --help`).

## Configure `mp`

On first run, `mp` creates `.mp_config` in your platform user config directory and defaults `marketplace_path` to `~/marketplace`. Point it to your local `content-hub` checkout root before running repository commands (`build`, `validate`, `test`, `pack`, `push`, `pull`, `describe`):

```bash
mp config --root-path /path/to/content-hub --display-config
```

For all configuration flags (`--processes`, `--gemini-api-key`, `--gemini-concurrency`), see [commands/config.md](commands/config.md).

## IDE Configuration

To run or debug `mp` from an IDE, set the Python interpreter to the virtual environment inside `packages/mp`:

- macOS / Linux: `packages/mp/.venv/bin/python`
- Windows: `packages\mp\.venv\Scripts\python.exe`
