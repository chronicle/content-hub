# `mp test`

Run pre-build `pytest` unit test suites for one or more integrations in parallel.

## Usage

```bash
mp test [OPTIONS]
```

## Options

Exactly one of `--integration` (`-i`) or `--repository` (`-r`) must be provided:

| Option | Shorthand | Description | Type | Default |
| :--- | :--- | :--- | :--- | :--- |
| `--integration` | `-i` | Test one or more specified integrations (repeatable). | `list[str]` | `[]` |
| `--repository` | `-r` | Test all integrations in specified repositories (`google` or `third_party`). | `list[RepositoryType]` | `[]` |
| `--raise-error-on-violations` | | Treat runtime warnings as errors. | `bool` | `False` |
| `--quiet` | `-q` | Log less on runtime. | `bool` | `False` |
| `--verbose` | `-v` | Log more on runtime. | `bool` | `False` |

## Execution Behavior

- For each target integration containing a `tests/` directory, `mp test` executes `run_pre_build_tests.sh` (or `run_pre_build_tests.bat` on Windows), adds `soar_sdk` from `.venv` to `PYTHONPATH`, runs `pytest --json-report --json-report-file=.report.json ./tests`, parses and removes `.report.json`, and prints a consolidated report.
- When `GITHUB_ACTIONS=true` is not set, `mp test` also writes a temporary HTML report and calls `webbrowser.open()` (prefix with `BROWSER=true` in headless or automated shells to suppress opening a browser).
- Exits with code `1` if any integration test suite fails.
- **Virtual environment caching**: `run_pre_build_tests.sh` runs `uv sync --dev` only when `<integration>/.venv` does not already exist. After editing an integration's `pyproject.toml` or `uv.lock`, run `uv sync --dev` inside that integration directory (or remove its `.venv`) before re-running `mp test`.

## Examples

### Test specific integrations
```bash
BROWSER=true mp test --integration my_integration --integration another_integration
```

### Test all commercial integrations
```bash
BROWSER=true mp test --repository google
```
