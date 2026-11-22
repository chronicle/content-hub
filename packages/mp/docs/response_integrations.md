# Google SecOps Response Integrations Guide

## Overview

The `mp` CLI manages the full lifecycle of response integrations in the Google SecOps Content Hub, from local authoring and testing to SOAR artifact compilation and environment deployment.

## Integration States & Directory Layout

Response integrations live under `content/response_integrations/` across repository tiers (`google/`, `third_party/community/`, `third_party/partner/`, `power_ups/`, or `custom/`).

Integrations exist in two representations:

- **Non-built (source)**: Human-editable YAML metadata, Python 3.11 modules using `soar_sdk` and `TIPCommon`, `uv` dependency lockfiles, and `pytest` tests.
- **Built (`out/`)**: Compiled JSON definitions (`.def`, `.actiondef`, `.connectordef`, `.jobdef`), import-flattened scripts (`ActionsScripts/`, `ConnectorsScripts/`, `JobsScrips/`, `Managers/`), and resolved binary `.whl` files (`Dependencies/`).

### Non-Built Source Structure

```text
<integration_name>/
├── __init__.py                 # Empty package marker
├── .python-version             # Pinned to 3.11
├── pyproject.toml              # Project metadata, version, and dependencies
├── uv.lock                     # Locked dependency graph
├── definition.yaml             # Integration-level metadata and configuration parameters
├── release_notes.yaml          # Customer-facing version history
├── core/                       # Shared managers, API clients, auth, constants, dataparsers
├── actions/                    # <action_name>.py and matching <action_name>.yaml
├── connectors/                 # <connector_name>.py and matching <connector_name>.yaml
├── jobs/                       # <job_name>.py and matching <job_name>.yaml
├── widgets/                    # Optional HTML/widget templates and metadata
├── resources/                  # logo.svg, image.png, *_JsonResult_example.json, ai/*.yaml
└── tests/                      # Black-box integration_testing / pytest suite
```

## Core Integration Workflow with `mp`

Ensure `mp` points to your `content-hub` checkout first:

```bash
mp config --root-path /path/to/content-hub
```

### 1. Format & Lint Code

```bash
mp format content/response_integrations/third_party/community/my_integration
mp check content/response_integrations/third_party/community/my_integration --static-type-check --raise-error-on-violations
```

### 2. Validate Structure & Metadata

Runs all 23 pre-build integration validators (`uv.lock` sync, version bump/consistency, SSL parameters, Ping action, JSON result examples, release notes, fields, structure, and dependencies):

```bash
mp validate integration my_integration
```

### 3. Run Pre-Build Unit Tests

Creates `<integration>/.venv` (if not present), adds `soar_sdk` to `PYTHONPATH`, and executes `pytest`:

```bash
mp test --integration my_integration
```

### 4. Build or Deconstruct

Compile the integration into `out/content/response_integrations/...`:

```bash
mp build integration my_integration
```

Convert a built integration back into non-built source layout:

```bash
mp build integration my_integration --deconstruct --src /path/to/built_dir --dst /path/to/output_dir
```

### 5. Package or Push to a SecOps Environment

Create a SOAR-importable `.zip` archive in `out/pack/`:

```bash
mp pack integration my_integration --non-interactive
```

Or build, auto-bump the dev minor version, and upload directly to a logged-in SecOps tenant:

```bash
mp login --gcp --api-root "https://us-chronicle.googleapis.com/v1alpha/projects/<PROJECT>/locations/us/instances/<INSTANCE_UUID>"
mp push integration my_integration
```

## Key Technical Notes

- **Import Restructuring (`libcst`)**: During `mp build`, imports from `soar_sdk.*` and relative `.core` imports are rewritten into flat top-level imports expected by the SOAR runtime; `--deconstruct` reverses this transformation and ensures `from __future__ import annotations` is present.
- **Binary Wheel Resolution**: During build, `mp` exports production dependencies via `uv export` and downloads platform-compatible binary wheels (`--only-binary=:all:`). If a dependency only publishes an sdist on PyPI, add its explicit source URL with `uv add "<pkg> @ <url>"`.
- **Unique Identifiers**: Full repository builds (`mp build repository google third_party`) verify that no duplicate integration identifiers exist across commercial and third-party tiers.
