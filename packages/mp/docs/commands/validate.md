# `mp validate`

Validate integrations and playbooks in the Content Hub before building or opening a pull request.

## Usage

```bash
mp validate <integration|playbook|repository> [TARGETS]... [OPTIONS]
```

## Subcommands

### `integration`

Validate one or more response integrations.

```bash
mp validate integration <INTEGRATIONS>... [--quiet|-q] [--verbose|-v]
```

Runs 23 integration validators, including:
- `pyproject.toml`, Python `3.11` requirement, `uv.lock` consistency (`uv lock --check`), required dev dependencies (`soar-sdk`, `pytest`, `pytest-json-report`), and dependency providers.
- Version consistency across `pyproject.toml` and `release_notes.yaml`, `YYYY-MM-DD` release-note publish date format, and PR version-bump checks against `origin/main` when `GITHUB_PR_SHA` is set in the environment (for local PR simulation on a committed branch: `GITHUB_PR_SHA=$(git rev-parse HEAD) mp validate integration <name>`).
- Required `Ping` action and Ping message format, `Verify SSL` parameters on integrations and connectors, documentation links, support email, description and field length/naming constraints, JSON result example files, ontology mapping rules when connectors exist, empty `__init__.py` files, no disabled/custom components, and sanitized `tests/config.json`.

### `playbook`

Validate one or more playbooks.

```bash
mp validate playbook <PLAYBOOKS>... [--quiet|-q] [--verbose|-v]
```

Runs 10 playbook validators: unique playbook names, referenced blocks existence, loop step rules, step parameters, valid environments (`*` or `Default Environment`), block-to-playbook environment matching, no overviews inside blocks, allowed overview roles, debug data checks, and version bump against `origin/main` (when `GITHUB_PR_SHA` is set).

### `repository`

Validate entire content repositories in parallel.

```bash
mp validate repository <REPOSITORIES>... [--quiet|-q] [--verbose|-v]
```

Valid `REPOSITORIES` values:
- `google`: Commercial response integrations.
- `third_party`: Community, partner, and power-up response integrations.
- `playbooks`: All playbooks.
- `all_content`: Commercial integrations, third-party integrations, and playbooks.

## Output & Exit Status

- Prints a structured CLI report. When `GITHUB_ACTIONS=true` is not set, also writes a temporary HTML report and calls `webbrowser.open()` (prefix with `BROWSER=true` in headless or automated shells to suppress opening a browser). When `GITHUB_ACTIONS=true`, writes a Markdown summary report instead.
- Exits with status code `1` if any validation fails.

## Examples

### Validate a specific integration (suppressing browser launch)
```bash
BROWSER=true mp validate integration my_integration
```

### Validate a playbook including version bump against `origin/main`
```bash
BROWSER=true GITHUB_PR_SHA=$(git rev-parse HEAD) mp validate playbook my_playbook
```

### Validate the third-party repository
```bash
BROWSER=true mp validate repository third_party
```

---

## Deprecated Usage

Flag-based invocation directly on `mp validate` (`--integration`, `--playbook`, `--repository`) is deprecated. Use the `integration`, `playbook`, and `repository` subcommands instead.
