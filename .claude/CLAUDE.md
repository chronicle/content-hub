# Content-Hub Development Guide


When launching sub agents, use claude-sonnet-4-6 as the model (sonnet). Available models: claude-sonnet-4-6, claude-opus-4-6.

Never commit with the co-authored message

## Project Overview

This is the **Google SecOps Content Hub** — a community-contributed open-source repository for
enhancing the Google SecOps platform. It contains:

- **Response Integrations** — Python scripts connecting Google SecOps to third-party tools (actions,
  connectors, jobs).
- **Playbooks** — Automated incident response workflows (YAML-based).

Only response integration and playbook content is currently supported via the contribution workflow.

---

## Repository Structure

```
content/
├── response_integrations/
│   ├── google/              # Google-maintained (migrated from tip-marketplace)
│   ├── third_party/
│   │   ├── community/       # Community-contributed integrations (57)
│   │   └── partner/         # Partner-supported integrations (31)
│   └── power_ups/           # Google-developed utility packs (11)
└── playbooks/               # Ignore — do not review or modify

packages/
├── tipcommon/               # TIPCommon library (base classes, utilities)
│   └── whls/                # Pre-built wheel files
├── envcommon/               # EnvironmentCommon library (TIPCommon dependency)
│   └── whls/
├── integration_testing/     # Shared black-box test utilities (source)
├── integration_testing_whls/ # Pre-built test utility wheels
└── mp/                      # `mp` CLI tool

tools/
└── migration/               # Migration pipeline (migrate.py, generate_test_mocks.py)

docs/                        # Documentation
```

---

## Ignore Patterns

Do not review or modify files matching:

- `content/playbooks/**`

---

## Tooling

### `mp` CLI (Marketplace Tool)

The `mp` tool is the official CLI for developing, validating, and deploying integrations.
On Windows, use `wmp` instead of `mp`.

**Dev environment:**
```bash
mp dev-env login --api-root <soar_url> --api-key <api_key>
mp dev-env pull integration <integration_name> [--dst <destination>]
mp dev-env push integration <integration_name> [--staging] [--custom]
mp dev-env pull playbook <playbook_name> [--include-blocks]
mp dev-env push playbook <playbook_name> [--include-blocks]
```

**Build (use subcommand form — the `--integration` flag form is deprecated):**
```bash
mp build integration <integration_name>          # source → deployable
mp build integration <integration_name> -d       # deconstruct: deployable → source
mp build playbook <playbook_name>
mp build playbook <playbook_name> -d
mp build repository third_party                  # values: google, third_party, custom, playbooks
```

**Validate:**
```bash
mp validate integration <integration_name>
mp validate integration <integration_name> --only-pre-build
mp validate playbook <playbook_name>
mp validate repository third_party               # values: google, third_party, playbooks (no custom)
```

**Code quality:**
```bash
mp check path/to/file.py                         # lint (--changed-files diffs vs HEAD)
mp check --changed-files --static-type-check
mp check path/to/file.py --fix
mp format path/to/file.py                        # ruff format (--changed-files diffs vs origin/develop)
mp format --changed-files
mp test --integration <name>                     # lint + type-check + unit tests
mp test --repository third_party
mp describe action --integration <name> --all    # generate AI descriptions via Gemini
```

> Note: `--changed-files` baselines differ: `mp check` diffs against **HEAD**, `mp format` diffs against **`origin/develop`**.
> Warning: `origin/develop` does not exist in content-hub (default branch is `main`). Prefer
> providing explicit file paths to `mp format` instead of `--changed-files`.

See [`/packages/mp/README.md`](/packages/mp/README.md) for full documentation.

### Validation System (`mp validate`)

`mp validate` runs 22 pre-build validators. Key checks that commonly block PRs:

- **Structure** — required files/directories exist
- **Ping action** — must exist
- **Version bump** — version must be incremented when modifying existing content (CI only)
- **Version consistency** — pyproject.toml version must match latest release_notes.yaml version
- **SSL parameter** — Verify SSL must exist with correct default in definition.yaml
- **JSON result examples** — required for every action with `add_result_json()`/`self.json_results`
- **Empty `__init__.py`** — source dir init files must be empty (only license headers)
- **Support email** — required in pyproject.toml description for partner integrations
- **Release notes date** — `publish_time` must be valid YYYY-MM-DD
- **Test config** — `tests/config.json` must exist
- **Dependency provider** — dependencies must come from PyPI, not internal registries
- **Required dev deps** — pytest, soar-sdk, TIPCommon, EnvironmentCommon, integration-testing

### Package Manager

Use **`uv`** for dependency management (not pip). Python version is typically `>=3.11,<3.12`.

Each integration is an independent Python project with its own `.venv` (created by `uv sync --dev` or `mp test`).

### TIPCommon & EnvironmentCommon

Foundational libraries for building integrations. Always use the **latest versions** from
`packages/tipcommon/whls/` and `packages/envcommon/whls/`. Check those directories for current
wheel files before adding.

```bash
# Relative path depth varies by integration category:
#   third_party/community/ or third_party/partner/ → ../../../../../packages/ (5 levels)
#   google/                                        → ../../../packages/ (3 levels)
uv add <relative_path>/packages/tipcommon/whls/TIPCommon-<VERSION>-py3-none-any.whl
uv add <relative_path>/packages/envcommon/whls/EnvironmentCommon-<VERSION>-py3-none-any.whl
```

If you add `TIPCommon`, you **must** also add `EnvironmentCommon`.

### SOAR SDK

Add as a **dev-only** dependency — never production. (The SDK is pre-installed at runtime on the
Google SecOps platform; adding it to production deps breaks execution.)

```bash
uv addc --dev git+https://github.com/chronicle/soar-sdk.git
```

### Integration Testing Package

Add per-integration for black-box/integration tests (use the pre-built wheel):

```bash
uv add <relative_path>/packages/integration_testing_whls/integration_testing-<VERSION>-py3-none-any.whl --dev
```

### Linting & Formatting

Use **`ruff`** via `mp check` and `mp format`. Use `--raise-error-on-violations` to fail CI on lint errors.

---

## Integration Structure

Every integration lives in `content/response_integrations/third_party/community/<name>/` or
`.../partner/<name>/`. All file names must be in **snake_case**.

```
integration_name/
├── actions/             # Action scripts (.py) and definitions (.yaml)
├── core/                # API client, auth, data models, utilities
├── connectors/          # Connector scripts (.py) and definitions (.yaml)
├── jobs/                # Job scripts (.py) and definitions (.yaml)
├── widgets/             # HTML widgets (.html) and definitions (.yaml)
├── resources/           # JSON result examples, images, logo
├── tests/
│   ├── common.py
│   ├── conftest.py
│   ├── config.json      # Test configuration (integration config params)
│   ├── core/            # Mock infrastructure
│   │   ├── product.py   # Fake API returning canned data
│   │   └── session.py   # HTTP interceptor routing to product mock
│   ├── test_defaults/   # Import sanity tests
│   └── test_actions/    # Action unit tests
├── definition.yaml      # Integration metadata (ID, config schema, author)
├── pyproject.toml       # Dependencies and build settings
├── release_notes.yaml   # Version history
├── ontology_mapping.yaml
├── .python-version
└── uv.lock
```

### Minimum Required Implementation

Every integration must have at minimum:

1. A core client class handling API communication
2. A `ping.py` / `ping.yaml` action to verify connectivity
3. At least one service-specific action
4. Comprehensive tests for all components
5. Proper error handling and type hints throughout

---

## Universal Script Conventions

These apply to **all** script types (actions, connectors, jobs):

- `from __future__ import annotations` — required at the top of every script
- Use `TYPE_CHECKING` guard for type-only imports to avoid runtime overhead:
  ```python
  from typing import TYPE_CHECKING
  if TYPE_CHECKING:
      from TIPCommon.base.interfaces import ApiClient
      from TIPCommon.types import Contains
  ```
- Always guard the entrypoint: `if __name__ == "__main__": main()`
- Start execution by calling `.run()` (actions) or `.start()` (connectors, jobs) on the class instance

---

## Two-Phase Parameter Handling Pattern

All script types split parameter handling into two phases — always store both raw and typed values on `self.params`:

```python
# Phase 1: extract raw string
self.params.tags_string = extract_job_param(param_name="Tags", ...)

# Phase 2: validate/parse to typed value
self.params.tags = validator.validate_csv(param_name="Tags", csv_string=self.params.tags_string)
```

`ParameterValidator` methods include: `validate_json`, `validate_csv`, `validate_positive`, and more.

---

## Script Patterns

### Action Pattern

```python
from __future__ import annotations
from typing import TYPE_CHECKING
from TIPCommon.base.action import Action
from TIPCommon.extraction import extract_action_param
from TIPCommon.validation import ParameterValidator

if TYPE_CHECKING:
    from TIPCommon.base.interfaces import ApiClient
    from TIPCommon.types import Contains

SCRIPT_NAME: str = "Action Name"

def main() -> None:
    MyAction(name=SCRIPT_NAME).run()

class MyAction(Action):
    def _extract_action_parameters(self) -> None: ...
    def _validate_params(self) -> None: ...
    def _init_api_clients(self) -> Contains[ApiClient]: ...
    def _perform_action(self, client) -> None: ...

if __name__ == "__main__":
    main()
```

### Connector Pattern

Connectors ingest Alerts (not Cases — Cases are created automatically by the platform).

```python
from __future__ import annotations
from TIPCommon.base.connector import Connector
from TIPCommon.data_models import BaseAlert
from TIPCommon.extraction import extract_connector_param
from TIPCommon.validation import ParameterValidator
from soar_sdk.SiemplifyConnectorsDataModel import AlertInfo

def main() -> None:
    MyConnector(script_name="Connector Name").start()

class MyConnector(Connector):
    def extract_params(self) -> None:          # no underscore prefix
        self.params.foo = extract_connector_param(siemplify=self.siemplify, param_name="Foo", ...)

    def validate_params(self) -> None:
        validator = ParameterValidator(self.siemplify)
        self.params.foo_typed = validator.validate_json(...)

    def init_managers(self) -> None: ...       # initialize API clients (or no-op)

    def get_alerts(self) -> list[BaseAlert]:
        return [BaseAlert(raw_data=..., alert_id=...)]

    def create_alert_info(self, alert: BaseAlert) -> AlertInfo:
        alert_info = AlertInfo()
        alert_info.alert_id = alert.alert_id
        alert_info.display_id = alert.raw_data["display_name"]
        alert_info.events = alert.raw_data["events"]
        return alert_info

if __name__ == "__main__":
    main()
```

**Rule:** Any integration containing a connector **must** also include `integration_mapping_rules.yaml`
with **Start Time** and **End Time** mapped. Without these, alert grouping breaks.

### Job Pattern

Jobs synchronize data between Google SecOps and a third-party product. They differ from connectors:
methods are underscore-prefixed and the SOAR handle is `self.soar_job`.

```python
from __future__ import annotations
from typing import TYPE_CHECKING
import TIPCommon.consts
from TIPCommon.base.job import Job
from TIPCommon.extraction import extract_job_param
from TIPCommon.validation import ParameterValidator

if TYPE_CHECKING:
    from TIPCommon.base.interfaces import ApiClient
    from TIPCommon.types import Contains

def main() -> None:
    MyJob(name="Job Name").start()

class MyJob(Job):
    def _extract_job_params(self) -> None:     # underscore prefix
        self.params.foo_string = extract_job_param(siemplify=self.soar_job, param_name="Foo", ...)

    def _validate_params(self) -> None:
        validator = ParameterValidator(self.soar_job)
        self.params.foo = validator.validate_positive(param_name="Foo", value=self.params.foo_string)

    def _init_api_clients(self) -> Contains[ApiClient]: ...

    def _perform_job(self) -> None:
        # Incremental sync pattern — always use this:
        last_run = self._get_job_last_success_time(
            offset_with_metric={"hours": self.params.max_hours_back},
            time_format=TIPCommon.consts.UNIX_FORMAT,
        )
        # ... do work ...
        self._save_timestamp_by_unique_id(self.job_start_time)

if __name__ == "__main__":
    main()
```

Key Job platform APIs in `_perform_job()`:
- `self.soar_job.get_cases_ids_by_filter(status, tags, environments, update_time_from_unix_time_in_ms, ...)`
- `self.soar_job.get_alerts_ticket_ids_by_case_id(case_id)`
- `self.soar_job.add_comment(comment, case_id, alert_id)`
- `self.params.environment_name` — built-in, available in all jobs

---

## Playbook Structure

Playbooks live in `content/playbooks/third_party/community/<name>/` or `.../partner/<name>/`.
All file names must be **snake_case**.

```
playbook_name/
├── steps/               # One .yaml file per step
├── widgets/             # Paired .html + .yaml per widget
├── definition.yaml      # Metadata; identifier field is used to link blocks
├── display_info.yaml    # Display name, author, description for Content Hub UI
├── overviews.yaml       # Summary shown in the Google SecOps UI
├── release_notes.yaml   # Version history (dates in YYYY-MM-DD)
└── trigger.yaml         # Single trigger definition
```

**Trigger types:** `alert`, `entity`, `manual`

**Step types:** Integration Action, Function, Condition, Block (sub-playbook)

**Block deduplication rule:** Never re-include a block that already exists in the repo. Instead,
find the existing block's `definition.yaml`, copy its `identifier` field, and set it as the
`value` of the `NestedWorkflowIdentifier` parameter in the referencing step.

**Contribution:**
```bash
mp dev-env pull playbook <name> --dest <folder>
mp build playbook <name> -d --src <exported_zip>  # manual deconstruct
mp validate playbook <name>
```

---

## Contribution & PR Process

- Fork the repo; submit PRs against `main`.
- **Version bump required** when modifying existing content.
- Run `mp validate integration <name>` — all checks must pass before requesting review.
- PRs opened as Draft must be marked "Ready for Review" once checks pass.
- PR title convention: `[Optional Buganizer ID: 123456789] Short description`
- No PII, internal URLs, or internal-only configs in any PR.

---

## Key Principles

* **Production-Ready SecOps:** Code must be resilient. Implement defensive programming, proactive
  error handling, and structured logging.
* **Security-First:** Python code must be hardened against intent-based or accidental misuse.
* **Readability & Maintainability:** Code is read more often than it is written. Use clear,
  descriptive naming and modular logic.
* **Performance:** Efficiency is critical in high-throughput environments. Avoid blocking calls in
  asynchronous contexts.
* **PII & Secret Sanitization:** Never allow Personally Identifiable Information (PII) or secrets to
  persist in logs, metadata, or telemetry.
    * **No Hardcoded Secrets:** Use secret managers for keys and tokens.
    * **Log Redaction:** Mask sensitive data fields before outputting to logs.
    * **Data Minimization:** Process only the absolute minimum data required for the operation.

---

## Security & Reliability

### Safe Path Handling

* **Mandatory `pathlib`:** Always use `pathlib.Path` for file system operations.
* **Avoid String Concatenation:** Do not use raw string concatenation (e.g., `folder + "/" + file`)
  or `os.path.join`.

> **Claude Action:** Proactively suggest refactoring any manual path manipulation to use
`pathlib.Path` objects and the `/` operator.

### Input & Execution Safety

* **No f-string SQL queries:** Always use parameterized queries to prevent SQL injection.
* **Safe Loading:** Use `yaml.safe_load()` instead of `yaml.load()` and `json.loads()` to prevent
  arbitrary code execution.

### Path-Specific Security Enforcement

The following rules apply strictly to `content/response_integrations/**`:

* **No Shell Execution:** Avoid `subprocess.run(..., shell=True)`. Always provide arguments as a
  list to prevent shell injection.
* **Prohibited Functions:** Use of `eval()`, `exec()`, or `input()` is strictly forbidden in
  production logic.

### Logging & Observability

* **No PII in Logs:** Never log secrets, API keys, tokens, or Personally Identifiable Information.

---

## Modern Python Patterns

### Asynchronous Programming

* **Non-blocking I/O:** Use `async` and `await` for network requests (e.g., `httpx` or `aiohttp`).
* **Avoid Blocking Calls:** Never use `time.sleep()` in `async def`. Use `asyncio.sleep()`.
* **Concurrency:** Use `asyncio.gather` for parallel I/O tasks.

### Static Type Checking

* All function parameters and return types **must** be annotated.
* Use the pipe operator for unions (e.g., `str | None`) instead of `Optional` (Python 3.10+).
* Use Pydantic for data validation and serialization.

---

## Docstrings & Documentation

Follow **Google Style Docstrings**.

* Use `"""Docstring"""` for all modules, classes, and functions.
* Do **not** repeat types in `Args` or `Returns` — infer from type hints.
* **Mandatory "Raises":** Document all intentionally raised exceptions.

```python
def process_hub_config(config_path: Path, retry_count: int = 3) -> dict[str, Any]:
    """Processes the central hub configuration file.

    Args:
        config_path: The filesystem path to the YAML configuration.
        retry_count: Number of attempts to read the file if busy.

    Returns:
        A dictionary representing the validated configuration.

    Raises:
        FileNotFoundError: If the config_path does not exist.
        RuntimeError: If the configuration is malformed or inaccessible.
    """
```

---

## Integration-Specific Requirements

> **Claude Action:** The following rules apply **strictly** to changes in `content/response_integrations/**`.

### Testing

All new features, bug fixes, or integrations **must** include corresponding unit tests.

* **Framework:** `pytest`
* **Reference "Golden Tests":**
    * `content/response_integrations/third_party/telegram/tests/`
    * `content/response_integrations/third_party/sample_integration/tests/`
* **Mocking:** Follow patterns in the reference examples. Never make real network calls in tests.
* **Run tests:** `mp test --integration <name>` (runs lint + type-check + unit tests)

> **Claude Action:** If files are added/modified in this path without a corresponding test file,
> flag it and offer to generate a test suite modeled after the Telegram or Sample Integration patterns.

### Mock Infrastructure Pattern

The test mock chain works by intercepting HTTP calls at the `requests.Session` level:

```
Test → Action.main() → Manager → requests.Session (monkeypatched)
  → MockSession matches URL via @router decorators → Product mock returns canned data
  → MockResponse wraps it → Manager processes as real → Test asserts on action_output
```

**`tests/core/product.py`** — Dataclass simulating the third-party API:
```python
@dataclasses.dataclass(slots=True)
class MyProduct:
    _fail_requests_active: bool = False
    _test_connectivity_response: SingleJson | None = None

    def test_connectivity(self) -> SingleJson:
        if self._fail_requests_active:
            raise Exception("Simulated API failure")
        return self._test_connectivity_response or {}

    def set_test_connectivity_response(self, response: SingleJson) -> None:
        self._test_connectivity_response = response

    @contextlib.contextmanager
    def fail_requests(self):
        self._fail_requests_active = True
        try:
            yield
        finally:
            self._fail_requests_active = False
```

**`tests/core/session.py`** — HTTP interceptor with `@router` decorators:
```python
class MySession(MockSession[MockRequest, MockResponse, MyProduct]):
    def get_routed_functions(self) -> list[RouteFunction]:
        return [self.test_connectivity]

    @router.get(r".*/api/v1/ping")
    def test_connectivity(self, request: MockRequest) -> MockResponse:
        try:
            data = self._product.test_connectivity()
            return MockResponse(content=data)
        except Exception as e:
            return MockResponse(content=str(e), status_code=500)
```

**`tests/conftest.py`** — Wiring fixtures:
```python
pytest_plugins = ("integration_testing.conftest",)

@pytest.fixture
def my_product() -> MyProduct:
    return MyProduct()

@pytest.fixture(autouse=True)
def script_session(monkeypatch: pytest.MonkeyPatch, my_product: MyProduct) -> MySession:
    session = MySession(my_product)
    if not use_live_api():
        monkeypatch.setattr(CreateSession, "create_session", lambda: session)
        monkeypatch.setattr("requests.Session", lambda: session)
    return session
```

**`tests/test_actions/test_ping.py`** — Standard ping test:
```python
class TestPing:
    @set_metadata(integration_config_file_path=CONFIG_PATH)
    def test_ping_success(self, script_session, action_output, my_product):
        my_product.set_test_connectivity_response({"ok": True})
        Ping.main()
        assert action_output.results.execution_state == ExecutionState.COMPLETED

    @set_metadata(integration_config_file_path=CONFIG_PATH)
    def test_ping_failure(self, script_session, action_output, my_product):
        with my_product.fail_requests():
            Ping.main()
        assert action_output.results.execution_state == ExecutionState.FAILED
```

### Validation & JSON Results

* **Detection:** An action returns JSON results if it has:
    * `result.add_result_json(...)`
    * `self.soar_action.json = ...`
    * `self.json_results = ...`
* **Requirement:** A corresponding JSON example file **must** exist in `resources/`.
* **Naming Convention:** `ActionName.py` → `resources/ActionName_JsonResult_example.json`
  (matches the action script filename, preserving case)

> **Claude Action:** If a JSON result is detected but the `_JsonResult_example.json` file is missing
> in `resources/`, alert the contributor and offer to generate a placeholder JSON structure.


---

## Content Design Standards

> These standards apply to all integrations. See `.local/how-to-build-response-integration.md`
> for the full north-star guide.

### Target Persona

**Security Analysts** — not developers. They may know basic scripting but care about outcomes
(enrich IOCs, create tickets, contain endpoints), not API internals. Design for playbook
execution (99% of use cases).

### Integration Configuration Requirements

Every integration **must** have:

- **API Root** — endpoint URL parameter (exception: SDK-based integrations like boto3)
- **Verify SSL** — `Bool`, default `Enabled`, optional, description: "If selected, the
  integration validates the SSL certificate when connecting to {product name}. Selected by default."
- **Ping action** — no parameters, lightweight, uses only integration config inputs

### Ping Action Messages (Exact Format Required)

| Outcome | Message |
|:--------|:--------|
| Success | `Successfully connected to the {integration name} server with the provided connection parameters!` |
| Failure | `Failed to connect to the {product name} server! Error is {API error or traceback}` |

### Parameter Naming Rules

- **2-4 words**, fully explicit ("Organization ID" not "Org ID")
- Capitalized (except to, a, an, from), no special characters
- Do NOT dump API inputs — translate to user-friendly terms
- Use the same terminology as the product UI

### JSON Result Structures (4 Standard Types)

1. **Generic** — `{"field": "value"}` (single object, no entities)
2. **List** — `[{"field": "value"}, ...]` (array, no entities)
3. **Entity** — `[{"Entity": "id", "EntityResult": {...}}, ...]`
4. **Entity List** — `[{"Entity": "id", "EntityResult": [{...}, ...]}, ...]`

**Anti-patterns:** No dynamic top-level keys, no key-value pair arrays.

### is_success / Case Wall Guidelines

`is_success` controls playbook flow. **Only fail for unrecoverable misconfigurations:**

| Scenario | Fails Playbook? |
|:---------|:----------------|
| Action succeeded / valid query with no results | No |
| Entity enrichment: none enriched | No |
| Invalid config parameter / wrong org name | **Yes** |
| Async action timed out | **Yes** |
| Invalid query | **Yes** |

**Key rule:** "No results found" should NEVER fail the playbook.

### Output Message Templates

- **Success (entities):** `Successfully {activity} on the following entities using {integration}: {identifiers}.`
- **Failure (entities):** `Action wasn't able to {activity} on the following entities using {integration}: {identifiers}.`
- **Error prefix:** `Error executing action "{action name}". Reason: {specific error}`
- **Query success:** `Successfully returned results for the query "{query}" in {integration}.`
- **Query no results:** `No results were found for the query "{query}" in {integration}.`

### Required for List/Search Actions

- **Max Results To Return** parameter — mandatory for any action returning multiple results
  (platform limit: 20 MB JSON). Default 50, max typically 1000.

### Time Handling (Standard 3-Parameter Pattern)

For time-scoped actions, use: `Time Frame` (DDL with Last Hour/6H/24H/Week/Month/Custom),
`Start Time` (ISO 8601, mandatory if Custom), `End Time` (ISO 8601, defaults to now).

### Widgets

Every action with a JSON Result **must** have a corresponding widget.

---

## Migration Context

### Active Migration: tip-marketplace → content-hub

~289 integrations are being migrated from the legacy `tip-marketplace` repo. Key details:

- **Migrated integrations land in `google/`** (not `third_party/`)
- **Legacy code gets `ruff.toml` exclusions** — lint bypassed during migration, fixed later

### Migration Pipeline (`tools/migration/`)

#### V2 Two-PR Workflow (recommended)

Migrations are split into two PRs to produce thin, reviewable GOB CLs:

**PR1 — Faithful migration (thin GOB CL):**
```bash
./tools/migration/migrate_integration.sh --minimal <IntegrationName>
```
- Structural migration + import rewrites only
- Skips Verify SSL, Ping rewrite
- Adds integration to validator exclusion lists (SSL + Ping)
- GOB CL diff: TIPCommon imports, version +1, license headers

**PR2 — Standardization (after PR1 merges):**
```bash
./tools/migration/standardize.sh <snake_name>
```
- Adds/fixes Verify SSL parameter
- Flags Ping actions needing message format updates
- Removes integration from exclusion lists
- Runs validate + lint + tests

#### Pipeline scripts

Four files form the pipeline:

**`migrate_integration.sh [--minimal] <IntegrationName> [destination_dir]`** — end-to-end orchestrator:
1. **Step 1** — `migrate.py`: structure/import migration from tip-marketplace format
2. **Step 1b** — Post-migration fixes: dual JSON result naming, ruff exclusions, release notes cleanup,
   removing incompatible legacy test files
3. **Step 2** — `generate_test_mocks.py`: auto-generates `product.py`, `session.py`, `conftest.py`,
   `test_ping.py` (skipped if hand-written mocks already exist)
4. **Step 3** — Lint & auto-fix: `mp check --fix --unsafe-fixes` + `mp format`
5. **Step 4** — Validate: `mp validate` + `mp check` + `mp build`
6. **Steps 5-6** — Test & verify: `pytest tests -v`, check for unguarded real HTTP calls

**`migrate.py`** — Core migration engine (uses `libcst` CST transformers):
- Widget JSON key capitalization
- `mp build -d` (deconstruct) for directory restructuring
- `ImportTransformer` rewrites all imports:
  - SDK: adds `soar_sdk.` prefix (`from SiemplifyAction import ...` → `from soar_sdk.SiemplifyAction import ...`)
  - Internal: `from IntegrationManager import ...` → `from ..core.IntegrationManager import ...`
  - TIPCommon: splits flat imports into submodule form (`from TIPCommon import extract_action_param`
    → `from TIPCommon.extraction import extract_action_param`) using 40+ function→submodule mappings
  - Test mocks: `from Tests.mocks.session import ...` → `from integration_testing.requests.session import ...`
- `SiemplifySession` → `requests.Session()` replacement (affects ~5 integrations)
- `_init_managers` → `_init_api_clients` rename (TIPCommon 2.x)
- Version bump, release notes, license headers, ruff exclusion
- Name collision detection: `http` → `http_integration`, `jira` → `jira_integration`, etc.

**`generate_test_mocks.py`** — Test mock infrastructure generator:
- **Endpoint detection** (6 methods): ENDPOINTS dict, f-strings, `urljoin()`, `.format()`,
  string concatenation, direct `requests.get/post` calls
- **Manager class parsing**: 3-tier heuristic (`*Manager.py` → `*manager.py` → any file with
  `self.session`), extracts public methods, detects HTTP method per method, traces auth flows
- **Ping action parsing**: finds which Manager method is called, extracts success/failure messages
- **Generated conftest patches all request backends**: `requests.Session`, `requests.session`,
  `requests.get/post/put/patch/delete/request`, `CreateSession.create_session`, `urllib.request.urlopen`
- **Config.json population**: handles booleans, certs (generates valid base64), service account JSON,
  passwords/tokens, URL params
- Pass rate: 119/292 (41%) on all unmigrated integrations; ~78% on standard REST integrations

### TIPCommon Version Conflict (Critical Knowledge)

| Component | TIPCommon Version | Why |
|:----------|:-----------------|:----|
| Integration production code | 1.0.10 (original) | Flat `from TIPCommon import X` works via `__init__.py` re-exports |
| `integration_testing` package | 2.0.0+ (dev dep) | Imports `from TIPCommon.base.action import ...` which only exists in 2.x |

**Resolution:** TIPCommon 1.x stays as prod dep; TIPCommon 2.x overrides it as dev dep.
`ImportTransformer` rewrites flat imports to 2.x submodule form so they work with both versions.

**Do NOT** install TIPCommon or integration_testing from source — always use pre-built `.whl` files.
Building from source causes `requests` library version conflicts.

### tip-marketplace Is Still Active

The legacy repo is not frozen — it continues to receive updates on `develop` → `rc` → `prod`.
Migrations must use the latest `rc` branch.

---

## Common PR Review Feedback (Avoid These)

Based on analysis of ~30 PRs, these are the most common review blockers:

1. **Import format** — must be relative (`from ..core.Manager import ...`)
2. **pyproject.toml** — correct `requires-python`, latest wheel versions, support email (partner)
3. **Release notes** — version must match pyproject.toml, current date, minimal for new integrations
4. **Missing AI descriptions** — always include `resources/ai/actions_ai_description.yaml`
5. **Missing production deps** — check that `pyproject.toml` deps match actual imports
6. **`__init__.py` must be empty** — only license headers allowed in source dirs
7. **JSON result examples** — required in `resources/` for any JSON-returning action
8. **Verify SSL** — must exist in `definition.yaml` with default `true`

---

Never run `grep` - ALWAYS use `rg` (ripgrep) - if not installed - ask the user to install it first and explain that it is a better method.


when running an integration (anything within content-hub/content/response_integrations
  for example) = you shuold source the existing .venv located within the integration directory


  # Troubleshooting Integration Test Import Errors

## The Problem
When running tests (`pytest tests`) inside an integration directory (e.g., `content/response_integrations/...`), you may encounter fatal import errors such as:
`ModuleNotFoundError: No module named 'OverflowManager'` (or `SiemplifyBase`, `SiemplifyDataModel`, etc.).

## The Root Cause
These errors do not usually originate from the integration's own source code. They come from shared testing dependencies (`integration_testing` and `TIPCommon`) which are installed into the integration's virtual environment from pre-compiled wheel (`.whl`) files.

These legacy `.whl` packages were built using top-level imports for SDK modules (e.g., `from OverflowManager import ...`). However, in the current environment, these modules have been relocated into the `soar_sdk` namespace (e.g., `soar_sdk.OverflowManager`). Because the legacy `.whl` files still look for the top-level modules, the test runner crashes.

## The Anti-Pattern (What NOT to do)
Do **NOT** attempt to "fix" this by rewriting the source code of `TIPCommon` or `integration_testing` to use the new `soar_sdk.` prefix. Furthermore, do **NOT** modify the integration's `pyproject.toml` to install these dependencies from local source folders instead of their `.whl` files.

Attempting to build these legacy packages from source alongside modern requirements causes massive dependency resolution conflicts (specifically around the `requests` library) when running `uv sync`.

## The Solution
The intended backward-compatibility mechanism is to manipulate the `PYTHONPATH` environment variable. By adding the `soar_sdk` site-packages directory to the `PYTHONPATH`, Python will treat the contents of `soar_sdk` as top-level modules, allowing the legacy wheel files to resolve their imports successfully without any code modifications.

### Step-by-Step Fix
Run the following commands from within the specific integration's root directory (where its `pyproject.toml` and `.venv` are located):

```bash
# 1. Add the soar_sdk directory to PYTHONPATH
# (Note: adjust 'python3.11' if your .venv uses a different Python version)
export PYTHONPATH=$PYTHONPATH:$(pwd)/.venv/lib/python3.11/site-packages/soar_sdk

# 2. Activate the virtual environment
source .venv/bin/activate

# 3. Run the tests
pytest tests
```

This will correctly bridge the gap between the legacy dependencies and the modernized `soar_sdk` namespace, allowing the test suite to execute successfully.




# Content-Hub Python Style Guide

## Introduction

This style guide outlines the coding conventions for Python code developed for the **Content-Hub**
open-source repository within Google SecOps.

Our mission is to ensure that all contributions are not just **functionally correct**, but *
*production-ready**. This means prioritizing security, observability, and resilient design patterns
that can withstand the demands of a Security Operations environment.

---

## Key Principles

* **Production-Ready SecOps:** Code must be resilient. Implement defensive programming, proactive
  error handling, and structured logging.
* **Security-First:** Python code must be hardened against intent-based or accidental misuse.
* **Readability & Maintainability:** Code is read more often than it is written. Use clear,
  descriptive naming and modular logic.
* **Performance:** Efficiency is critical in high-throughput environments. Avoid blocking calls in
  asynchronous contexts.
* **PII & Secret Sanitization:** Never allow Personally Identifiable Information (PII) or secrets to
  persist in logs, metadata, or telemetry.
    * **No Hardcoded Secrets:** Use secret managers for keys and tokens.
    * **Log Redaction:** Mask sensitive data fields before outputting to logs.
    * **Data Minimization:** Process only the absolute minimum data required for the operation.

---

## Security & Reliability

### Safe Path Handling

* **Mandatory `pathlib`:** Always use `pathlib.Path` for file system operations.
* **Avoid String Concatenation:** Do not use raw string concatenation (e.g., `folder + "/" + file`)
  or `os.path.join`.

> **Gemini Action:** Proactively suggest refactoring any manual path manipulation to use
`pathlib.Path` objects and the `/` operator.

### Input & Execution Safety

* **No f-string SQL queries:** Always use parameterized queries to prevent SQL injection.
* **Safe Loading:** Use `yaml.safe_load()` instead of `yaml.load()` and `json.loads()` to prevent
  arbitrary code execution.

### Path-Specific Security Enforcement

The following rules need to be tracked and reported in the following path: "
content/response_integrations/**"

* **No Shell Execution:** Avoid `subprocess.run(..., shell=True)`. Always provide arguments as a
  list to prevent shell injection.
* **Prohibited Functions:** Use of `eval()`, `exec()`, or `input()` is strictly forbidden in
  production logic.

### Logging & Observability

* **No PII in Logs:** Never log secrets, API keys, tokens, or Personally Identifiable Information (
  PII).

---

## Modern Python Patterns

### Asynchronous Programming

Since many SecOps workflows are I/O bound (API calls, logs), we leverage `asyncio`.

* **Non-blocking I/O:** Use `async` and `await` for network requests (e.g., using `httpx` or
  `aiohttp`).
* **Avoid Blocking Calls:** Never use `time.sleep()` or blocking socket operations inside an
  `async def` function. Use `asyncio.sleep()`.
* **Concurrency:** Use `asyncio.gather` for parallel I/O tasks where appropriate to improve
  performance.

### Static Type Checking

* **Strictness:** All function parameters and return types **must** be annotated.
* **Modern Syntax:** Use the pipe operator for unions (e.g., `str | None`) instead of `Optional` (
  Python 3.10+).

---

## Docstrings & Documentation

We follow the **Google Style Docstrings** with a focus on reducing "stale" information.

* **Triple Double Quotes:** Use `"""Docstring"""` for all modules, classes, and functions.
* **No Redundant Types:** Do **not** repeat types in the `Args` or `Returns` sections. Types should
  be inferred from the function signature's type hints.
* **Mandatory "Raises":** Explicitly document all exceptions that the function may intentionally
  raise.

```python
from pathlib import Path
from typing import Any


def process_hub_config(config_path: Path, retry_count: int = 3) -> dict[str, Any]:
    """Processes the central hub configuration file.

    Args:
        config_path: The filesystem path to the YAML configuration.
        retry_count: Number of attempts to read the file if busy.

    Returns:
        A dictionary representing the validated configuration.

    Raises:
        FileNotFoundError: If the config_path does not exist.
        RuntimeError: If the configuration is malformed or inaccessible.
    """
    if not config_path.exists():
        raise FileNotFoundError(f"Missing config at: {config_path}")

    # Body implementation...
    return {}
```

---

## Integration-Specific Requirements

> **Gemini Action:** The following rules apply **strictly** to changes made within the
`content/response_integrations/**` directory.

### Testing

All new features, bug fixes, or integrations added to `content/response_integrations/**` **must**
include corresponding unit tests to ensure production stability.

* **Framework:** Use `pytest` for test execution.
* **Reference Examples:** When generating or suggesting tests, Gemini **must** model the code after
  the **"Golden Tests"** found in:
    * `content/response_integrations/third_party/telegram/tests/`
    * `content/response_integrations/third_party/sample_integration/tests/`
* **Mocking:** Follow the mocking patterns established in the reference examples above. **Strict
  Rule:** Never make real network calls during unit tests.

> **Gemini Action:** If a contributor modifies or adds files in this path, check for a corresponding
> test file. If missing or incomplete, suggest generating a test suite modeled specifically after the
> patterns found in the Telegram or Sample Integration reference paths.

### Validation & JSON Results

For integrations utilizing the `TIPCommon` Action base class or standard result reporting, we
require explicit documentation of the output schema.

* **Detection:** Identify if an action returns a JSON result by looking for:
    * Calls to `result.add_result_json(...)`
    * Assignments to `self.soar_action.json = ...`
    * Assignments to `self.json_results = ...`
* **Requirement:** If a JSON result is detected, a corresponding JSON example file **must** exist in
  the integration's `resources/` directory.
* **Naming Convention:** The example file must match the action's filename (e.g., `ActionName.py`
  requires `resources/ActionName_JsonResult_example.json`).

> **Gemini Action:** If a JSON result assignment is detected but the corresponding
`_json_example.json` file is missing in the `resources/` folder, alert the contributor and offer to
> generate a placeholder JSON structure based on the code's logic.

---