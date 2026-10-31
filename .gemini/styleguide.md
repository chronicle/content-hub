# Content-Hub Response Integrations — Review Style Guide

Scope: `content/response_integrations/**` (Python actions, connectors, jobs, `core/`, `definition.yaml`,
component YAML, `release_notes.yaml`, `pyproject.toml`, `tests/`, `resources/`). The code is synchronous
Python 3.11 using `requests`, TIPCommon and the SOAR SDK; there is no asyncio. For files outside this scope
(parsers, `packages/`, playbooks), limit review to correctness and security findings.

Review priorities, in order: (1) backward compatibility, (2) release hygiene, (3) correctness and error
handling, (4) TIPCommon reuse and definition/code consistency, (5) tests, (6) hygiene the linter does not cover.
Do not repeat findings that `mp validate` / `mp check` already report on the PR; do not comment on legacy code
the PR does not touch; post one comment per distinct issue, not one per file or per occurrence.

The target user of every integration is a security analyst working through playbooks, not a software engineer.

## 1. Backward compatibility (blocking)

- Flag when an existing action, connector or job parameter becomes `is_mandatory: true`, or a new parameter is
  added with `is_mandatory: true` to an existing component. Saved instances and playbooks will break.
- Flag when a key is renamed or removed from an action's JSON result (`add_result_json`, `json_results`,
  `*_JsonResult_example.json`), or when a list result becomes a single object. Playbook placeholders depend on
  them.
- Flag when an action/connector/job `name`, `identifier`, script file name or display name changes, or when a
  file is renamed to snake_case without the old script being kept — unless the release note says the change is
  regressive.
- Flag when a shared helper's return type changes (e.g. `SingleJson` → `list[SingleJson]`) or when a legacy
  fallback is dropped (`param.Name or param.DisplayName`, legacy-API branch next to the 1P branch,
  `installedVersion` falsy check). Both legacy and 1P platform paths must keep working.
- Flag use of private SDK/TIPCommon members (`siemplify._…`, `settings._id`); they are not a stable contract.
- Flag changed `default_value`, `is_enable`, `entity_types`, `simulation_data_json` or parameter `type` in an
  existing YAML when the PR description does not explain it.

## 2. Release hygiene (blocking)

- Any change inside an integration directory requires: `version` in `pyproject.toml` incremented by exactly
  `+1.0`, the same version in `definition.yaml`, a new `release_notes.yaml` entry with that `version:`, and an
  updated `uv.lock` (`uv lock`). Flag when any of the four is missing. New integrations start at `1.0` with a
  single release-note entry.
- Release-note entry: `version:` (not `integration_version:`); `publish_time: 'YYYY-MM-DD'` equal to the planned
  release date — flag when it is earlier than the previous entry or in the past; `item_type` is one of
  Integration/Action/Connector/Job/Widget; `item_name` is that component's display name (for an Action, the
  action name, not the integration); newest entry last; omit `new: false`/`deprecated: false`; one
  customer-facing sentence, no code identifiers.
- `pyproject.toml`: description explains what the integration does and (partner integrations) ends with the
  support-contact sentence; `requires-python = "==3.11.*"`; dependencies added with `uv add` (flag
  `requirements.txt`); direct imports such as `requests` declared even if TIPCommon pulls them; latest
  `TIPCommon` / `integration_testing` wheel from `packages/`; no `environmentcommon` (merged into TIPCommon);
  `soar-sdk` only as a dev dependency.
- Images live in `resources/`; flag inline `svg_image` / `image_base64` in `definition.yaml` and legacy keys.
- Flag changes outside the integration the PR is about (other integrations, index files, file-mode changes,
  reformat-only hunks) and ask whether they are intentional.

## 3. Correctness, error handling and output

- Flag `except Exception: pass`, bare `except:`, and catches that only re-raise a generic `Exception`. Catch the
  specific exception (`requests.RequestException`, `json.JSONDecodeError`, `OSError`, the integration's own
  `*Error`) and re-raise with `raise X(...) from e`.
- Flag branching on error-message text (`"deletedfolder" in str(e)`); branch on status codes or typed
  exceptions.
- Flag manager/API-client methods whose HTTP call does not go through `validate_response`, and `except`
  branches that can never run because the validator already raised.
- Flag an action that returns `EXECUTION_STATE_COMPLETED` after an exception, or an `output_message` that does
  not say what happened.
- Playbook failure rules: "no results found" is a normal outcome, never `EXECUTION_STATE_FAILED`. Enrichment
  with zero results → `is_success=False`; a valid query with no results → `is_success=True`. Fail only for
  unrecoverable misconfiguration (invalid org, invalid list, bad query syntax) or async timeouts.
- Output messages follow the standard templates: success "Successfully {activity} on the following entities
  using {integration}: {ids}"; failure "Action wasn't able to {activity} on the following entities using
  {integration}: {ids}"; error prefix `Error executing action "{action name}". Reason: {error}`.
- Flag `data.get("key", {})` / `.get("key", [])` followed by `.get`, iteration or `sorted` on API data — JSON
  `null` yields `None`; use `data.get("key") or {}` and guard `None` before attribute access.
- Flag fetch-everything-then-filter-locally when the API accepts the filter (e.g. pass `guid=` to the search).
- Flag duplicate calls (same API request twice in one flow), `datetime.utcnow()` (use
  `datetime.now(timezone.utc)`), Python 2 remnants (`super(Cls, self)`, `.encode()` inside f-strings).
- Logging: `siemplify.LOGGER.exception(e)` for exceptions (not `print`, and not `LOGGER.error(msg)` plus
  `LOGGER.exception(e)` for the same error); failures at `error` level, not `debug`; never silently skip
  malformed items — log them. The SDK logger exposes `warn`, not `warning`.

## 4. TIPCommon, content design and definition ↔ code consistency

- Flag `siemplify.parameters.get(...)` / `siemplify.get_configuration(...)`; use `extract_action_param`,
  `extract_configuration_param`, `extract_connector_param` (with `input_type`, `is_mandatory`, `default_value`).
- Flag hand-rolled helpers that exist in TIPCommon: parameter validation (`TIPCommon.validation`,
  `validate_params`), `string_to_multi_value` and other `TIPCommon.transformation` functions, time constants,
  pagination (`_paginate_results`), `SingleJson` / `JSON` types. New managers should build on `TIPCommon.base`
  (`Action`, `Job`, `Connector`, `Apiable`, `Authable`).
- Flag a parameter extracted in Python that has no matching entry in the component YAML (and vice-versa), or
  whose YAML `type` / `default_value` / `is_mandatory` disagrees with the code (`input_type=int` vs
  `type: string`, code default `False` vs YAML `'true'`, `is_mandatory: true` plus a redundant emptiness check).
- Integration configuration: an **API Root** parameter (except SDK-based integrations such as boto3) and a
  **Verify SSL** boolean parameter defaulting to `true`. Parameter and action names are 2–4 capitalised words
  without special characters ("Organization ID", not "org_id"; `Contain Host`, `Add IP to Hotlist`), matching the
  product's own UI terminology.
- JSON results use one of the four standard shapes: generic `{"field": "value"}`, list `[{...}, ...]`, entity
  `[{"Entity": id, "EntityResult": {...}}]`, or entity list `[{"Entity": id, "EntityResult": [{...}]}]`. Flag
  dynamic top-level keys (`{"1": {...}, "2": {...}}`) — they break playbook placeholders. An action that sets a
  JSON result needs a matching `resources/<action_file>_JsonResult_example.json`.
- Flag action descriptions that list entity types the code does not handle (`SUPPORTED_ENTITY_TYPES`,
  `simulation_data_json`), and parameter descriptions that merely repeat the parameter name.
- Flag code copied verbatim from `base_action.py` / another script instead of calling it, and repeated literals
  that belong in `constants.py` (status codes, priorities, prefixes).

## 5. Security and secrets

- Flag real-looking hostnames, internal IPs, e-mails, serial numbers or customer IDs in `tests/mock_data.json`,
  `resources/*_JsonResult_example.json`, sample payloads and YAML defaults — they must be masked or generic.
- Flag credentials in URLs (`https://user:pass@…`), in log or output messages, in exception text that includes
  `response.content`, and secrets written to JsonResult or rendered by widgets with `safe_rendering: false`.
- `Verify SSL` must exist in `definition.yaml` (default true) **and** `verify_ssl` must reach every client or
  session, including SDK-built clients (boto3/STS). Flag `verify=False` and a `verify_ssl` that is read but never
  used.
- Flag per-request credentials or e-mails written into a shared `requests.Session.headers`; pass `headers=` per
  call.
- Flag archive extraction without path-traversal guards, `subprocess` with `shell=True`, `eval` / `exec` /
  `input`, and `yaml.load` without a safe loader.

## 6. Tests

- New or changed action/connector/job without a test under `tests/` is a blocking finding. Tests use the
  `integration_testing` black-box framework (`product.py`, `session.py`, `MockSession`, fixtures from
  `conftest.py`), modelled on `content/response_integrations/third_party/telegram/tests/` and
  `third_party/sample_integration/tests/` — never real HTTP.
- Each component needs at least one failure-path test (API error, missing entity, invalid parameter) in addition
  to the success path; keep `tests/test_defaults/test_imports.py` and `tests/test_actions/test_ping.py`.
- Flag asserts that cannot fail (`assert result` for a value that should be `""`), unused fixture parameters, and
  test names that do not state the scenario and expected outcome.

## 7. Hygiene the third-party linter does not cover

(Google integrations run ruff `ALL`; third-party, partner and power-up integrations run only `E,F,FA102,I`.)

- File names of actions, connectors, jobs and `core/` modules: `lower_snake_case.py` with the matching `.yaml`.
- `from __future__ import annotations` is the first import of every module; imports at top level only (no
  function-local imports, no `try: import … except ImportError: pass`); groups stdlib → third-party → `soar_sdk`
  → `TIPCommon` → relative `.core`; SDK imports via the `soar_sdk.*` namespace; TIPCommon 2.x imports from
  submodules (`from TIPCommon.extraction import extract_action_param`); local core imports relative; no wildcard
  imports.
- Type hints on every parameter and return (`-> None` included); parametrised generics (`dict[str, Any]`, never
  bare `dict` / `list`); `X | None` not `Optional`; `SingleJson` from `TIPCommon.types` for JSON dicts;
  annotation-only imports under `if TYPE_CHECKING:`; `slots=True` on dataclasses. Do not annotate attributes
  already annotated in the base class.
- Flag commented-out code, template or placeholder comments, `#wip`-style markers, unused variables, imports and
  constants, non-empty `__init__.py` (license header only), stray files (`requirements.txt`, wheels, scratch
  files).
- Keep `main()` and manager methods readable: extract repeated conditions into named helpers, return early
  instead of nesting, no static methods where a module function will do; functions above ~50 lines or 7 levels of
  nesting get a comment, not a blocker.
- Google-style docstrings on public `core/` functions; do not repeat types in `Args:` / `Returns:`. A `Raises:`
  section is optional. Docstrings are not required in tests.
- Formatting is ruff's job (`ruff format`, 120 columns, double quotes); only flag invalid `# noqa` /
  `# ruff: noqa` codes and files that obviously were not formatted.

## 8. Do not flag

- Anything already reported by `mp validate` or `mp check` on the PR (version/lock/release-note format, SSL
  parameter presence, Ping message wording, JSON example file presence, empty `__init__`, support e-mail).
- `asyncio` / `httpx` / "blocking call in async context" — the codebase is synchronous by design; SOAR async
  actions are polling re-runs via `is_first_run`, not coroutines.
- Missing `Raises:` sections, docstrings on tests, `pathlib` for one-off paths, `Enum` for test-only constants,
  pinning the SOAR SDK git dependency — maintainers have rejected these.
- Legacy modules the PR does not modify; CamelCase ↔ snake_case renames of existing files (that is a regression,
  see §1); `Verify SSL` defaults on per-action parameters.
