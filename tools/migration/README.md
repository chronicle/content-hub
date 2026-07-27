# Migration Pipeline

Tools for migrating integrations from [tip-marketplace](https://chronicle-soar.googlesource.com/tip-marketplace) (GOB) to [content-hub](https://github.com/chronicle/content-hub) (GitHub).

## Overview

The migration pipeline converts integrations from the legacy tip-marketplace format to the content-hub format. This involves:

- **Directory restructuring** — monolithic layout to deconstructed source (`ActionsScripts/` -> `actions/`, `Managers/` -> `core/`, etc.)
- **Import rewrites** — SDK prefix (`soar_sdk.`), TIPCommon submodule split, relative imports
- **Test generation** — mock infrastructure (`product.py`, `session.py`, `conftest.py`, `test_ping.py`)
- **Dependency management** — `requirements.txt` -> `pyproject.toml` + `uv.lock`
- **Metadata** — version bump, release notes, license headers

## Two-PR Workflow (V2)

Migrations are split into two PRs to produce thin, reviewable Gerrit CLs on tip-marketplace:

### PR1: Faithful Migration (`--minimal`)

Performs only the structural changes needed to make the integration work in content-hub. The resulting Gerrit CL (created automatically by the Louhi sync flow) has a thin diff vs. tip-marketplace — mainly TIPCommon import style changes, version +1, and license headers.

```bash
./tools/migration/migrate_integration.sh --minimal <IntegrationName>
```

**What it does:**
- Restructures directories (`mp build -d`)
- Rewrites all imports (SDK, TIPCommon, internal, test mocks)
- Renames `_init_managers` -> `_init_api_clients` (TIPCommon 2.x)
- Replaces `SiemplifySession` -> `requests.Session()` (5 integrations)
- Generates test infrastructure (product.py, session.py, conftest.py, test_ping.py)
- Bumps version by +1 and appends a migration release note
- Adds license headers to all source files
- Adds integration to ruff.toml exclusions (suppresses lint for legacy code)
- Adds integration to validator exclusion lists (SSL + Ping message format)
- Runs lint auto-fix, validation, and tests

**What it skips (deferred to PR2):**
- Adding/fixing the Verify SSL parameter
- Rewriting Ping action messages to standard format
- Version reset to 1.0
- Release notes history cleanup

**After PR1 merges:**
- The Louhi `[GitHub] Sync Content Hub to GOB` flow fires automatically
- A Gerrit CL is created on tip-marketplace with the minimal diff
- Reviewer approves the CL -> integration is now synced

### PR2: Standardization

Applies content-hub standards after the faithful migration has landed:

```bash
./tools/migration/standardize.sh <snake_name>
```

**What it does:**
- Adds/fixes Verify SSL parameter in `definition.yaml`
- Flags Ping actions that need message format updates
- Removes integration from validator exclusion lists
- Runs lint, validation, and tests

**After PR2 merges:**
- A second Gerrit CL is created with the improvement changes
- Reviewer can inspect exactly what was changed vs. the faithful migration

## Scripts

### `migrate_integration.sh`

End-to-end orchestrator. Runs all migration steps in sequence.

```
Usage: ./tools/migration/migrate_integration.sh [--minimal] <IntegrationName> [destination_dir]

  --minimal         Faithful migration only (skip Verify SSL, Ping rewrite).
                    For use with the two-PR workflow.
  IntegrationName   Name as it appears in tip-marketplace (e.g., UrlScanIo, Shodan)
  destination_dir   Where to place the migrated integration
                    (default: content/response_integrations/google_new_test)
```

**Steps:**

| Step | Description |
|------|-------------|
| 1 | `migrate.py` — structure/import migration |
| 1b | Post-migration fixes — JSON result naming, ruff exclusions, release notes cleanup, legacy test cleanup |
| 2 | `generate_test_mocks.py` — test mock generation (skipped if hand-written mocks exist) |
| 3 | `mp check --fix` + `mp format` — lint auto-fix |
| 4 | `mp validate` + `mp check` + `mp build` — validation |
| 5 | `pytest tests -v` — run tests |
| 6 | Verify no real HTTP calls in tests |

**Environment variables:**

| Variable | Default | Description |
|----------|---------|-------------|
| `PYTHON` | auto-detected | Python interpreter with `libcst` and `mp` available |
| `MIGRATION_BATCH_MODE` | `false` | Set to `true` when running multiple migrations in a batch (skips per-integration ruff.toml and mp config) |

**Prerequisites:**
- `mp`, `uv`, `addlicense` on PATH
- tip-marketplace cloned at `../tip-marketplace` (sibling to content-hub)
- Python 3.11 available

### `migrate.py`

Core migration engine using `libcst` CST transformers. Called by `migrate_integration.sh`.

```
Usage: python migrate.py <integrations_path> <dst_path> --tests-dir <tests_path>
                         [--integrations-list "Name1 Name2"]
                         [--skip-verify-ssl]
                         [--debug]

  integrations_path   Source integrations directory (e.g., ../tip-marketplace/Integrations)
  dst_path            Destination directory in content-hub
  --tests-dir         Path to tip-marketplace Tests directory
  --integrations-list Space-separated list of integration names to process
  --skip-verify-ssl   Skip adding/fixing the Verify SSL parameter (used by --minimal)
  --debug             Enable debug logging
```

**Transformations applied:**

| Category | Transformation | Produces GOB diff? |
|----------|---------------|-------------------|
| Structure | Directory deconstruction (`mp build -d`) | No (reversed by `mp build`) |
| Structure | snake_case directory naming | No (reversed by `mp build`) |
| Structure | stdlib/pip collision avoidance (`http` -> `http_integration`) | No |
| Imports | SDK prefix (`soar_sdk.`) | No (reversed by `mp build`) |
| Imports | Relative imports (`from ..core.Manager`) | No (reversed by `mp build`) |
| Imports | TIPCommon submodule split | **Yes** — `from TIPCommon import X` -> `from TIPCommon.extraction import X` |
| Imports | Test mock imports (`Tests.mocks` -> `integration_testing`) | No (tests not in build) |
| Code | `_init_managers` -> `_init_api_clients` | **Yes** — method rename |
| Code | `SiemplifySession` -> `requests.Session()` | **Yes** — 5 integrations only |
| Code | Verify SSL parameter (skippable with `--skip-verify-ssl`) | **Yes** — definition.yaml change |
| Metadata | Version bump (+1) | **Yes** — in `Integration-Name.def` and `RN.json` |
| Metadata | Migration release note appended | **Yes** — new entry in `RN.json` |
| Metadata | License headers (`addlicense`) | **Yes** — on all `.py` files |
| Metadata | `requires-python` upper bound (`>=3.11,<3.12`) | No (not in build output) |
| Metadata | ruff.toml exclusion | No (not in build output) |

**Key insight:** `mp build` reverses SDK prefix and relative imports back to the tip-marketplace style. The main sources of diff in a Gerrit CL are: TIPCommon imports, version bump, license headers, and method/session renames.

### `generate_test_mocks.py`

Generates test mock infrastructure by analyzing the integration's Manager class and Ping action.

```
Usage: python generate_test_mocks.py <integration_path>
```

**Generated files:**

| File | Description |
|------|-------------|
| `tests/core/product.py` | Fake API dataclass with `fail_requests()` context manager |
| `tests/core/session.py` | `MockSession` with `@router` decorated methods for each detected endpoint |
| `tests/conftest.py` | Pytest fixtures that monkeypatch all HTTP transports |
| `tests/test_actions/test_ping.py` | `test_ping_success` and `test_ping_failure` tests |
| `tests/common.py` | `INTEGRATION_PATH` and `CONFIG_PATH` constants |
| `tests/config.json` | Test configuration with mock values for integration parameters |

**Detection methods for endpoints:**
1. `ENDPOINTS` dict in Manager
2. f-string URL construction
3. `urljoin()` calls
4. `.format()` calls
5. String concatenation
6. Direct `requests.get/post` calls

**Pass rate:** ~41% on all unmigrated integrations; ~78% on standard REST integrations.

### `standardize.sh`

Applies content-hub standards to a previously migrated integration (PR2 of the two-PR workflow).

```
Usage: ./tools/migration/standardize.sh <integration_snake_name> [integration_parent_dir]

  integration_snake_name   snake_case name (e.g., certly, url_scan_io)
  integration_parent_dir   Parent directory (default: content/response_integrations/google)
```

**Steps:**
1. Adds/fixes Verify SSL parameter in `definition.yaml`
2. Checks Ping action messages and flags non-compliant ones for manual update
3. Removes integration from validator exclusion lists (`exclusions.yaml`)
4. Runs `mp check --fix` + `mp format` + `mp validate` + tests

## How the Louhi GOB Sync Works

When changes to `content/response_integrations/google/**` are merged to `main`, the Louhi flow `[GitHub] Sync Content Hub to GOB` triggers automatically:

1. **Build** — `mp build integration <name>` converts content-hub source to deployable format
2. **Compare** — For first-time migrations (no `.migration_ignore`), runs comparison tool and logs diffs as context (non-blocking)
3. **Copy** — Copies built artifacts to tip-marketplace
4. **CL** — Creates a Gerrit CL on tip-marketplace with the diff
5. **Notify** — Posts the CL link to Google Chat

The two-PR workflow ensures:
- **PR1 merge** -> thin Gerrit CL (mainly TIPCommon imports + version bump)
- **PR2 merge** -> improvements Gerrit CL (Verify SSL, Ping, etc.)

## Validator Exclusion Lists

During `--minimal` migration, integrations are added to exclusion lists to pass validation without Verify SSL or Ping message format changes. These lists live in:

```
packages/mp/src/mp/core/data/exclusions.yaml
```

| Key | Validator skipped |
|-----|------------------|
| `excluded_names_without_verify_ssl` | SSL Parameter validation |
| `excluded_names_without_ping_message_format` | Ping Message Format validation |

The `standardize.sh` script removes integrations from these lists after applying the fixes.

## Troubleshooting

### Import errors when running tests

If tests fail with `ModuleNotFoundError: No module named 'OverflowManager'` or similar:

```bash
export PYTHONPATH=$PYTHONPATH:$(pwd)/.venv/lib/python3.11/site-packages/soar_sdk
source .venv/bin/activate
pytest tests -v
```

This is caused by legacy wheel packages using top-level SDK imports. The fix is to add the `soar_sdk` directory to `PYTHONPATH`.

### `mp` command not found

The `mp` tool must be installed in a venv accessible on PATH:

```bash
export PATH="$(git worktree list | head -1 | awk '{print $1}')/.venv/bin:$PATH"
```

### tip-marketplace not found

Clone tip-marketplace as a sibling to content-hub:

```bash
cd ..
git clone https://chronicle-soar.googlesource.com/tip-marketplace
cd tip-marketplace && git checkout rc
```

### Validation fails on `exclusions.yaml`

If you see a YAML parse error in `exclusions.yaml`, check that no list key has `[]` (inline empty array) with block entries below it. The `--minimal` flag handles this, but manual edits may introduce it.
