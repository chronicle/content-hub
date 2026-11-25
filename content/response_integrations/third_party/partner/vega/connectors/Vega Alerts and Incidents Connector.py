"""
Vega Alerts and Incidents Connector.

Fetches Vega incidents and packages the top-N related signals as SOAR alerts
that share ``Vega:incident:<id>``. Case description (from incidentSummary) is
maintained by the Sync Alerts job (not this connector).
"""

from __future__ import annotations

import json
import sys
import time
from contextlib import contextmanager, suppress
from typing import TYPE_CHECKING, Any, Iterator

from soar_sdk.SiemplifyConnectors import SiemplifyConnectorExecution
from soar_sdk.SiemplifyUtils import output_handler

from ..core.AlertPackager import create_alerts
from ..core.constants import (
    CHECKPOINT_PROPERTY_KEY,
    CONNECTOR_NAME,
    INGEST_STOP_BUFFER_SECONDS,
    MAX_ALERTS_IN_CASE_DEFAULT,
    MAX_ALERTS_IN_CASE_MAX,
    MAX_ALERTS_IN_CASE_MIN,
    MAX_EVENTS_PER_ALERT_DEFAULT,
    MAX_EVENTS_PER_ALERT_MAX,
    MAX_EVENTS_PER_ALERT_MIN,
    PARAM_ACCESS_KEY,
    PARAM_ACCESS_KEY_ID,
    PARAM_ALERT_SEVERITIES,
    PARAM_ALERT_STATUSES,
    PARAM_ALERT_VERDICTS,
    PARAM_API_ROOT,
    PARAM_BACKFILL,
    PARAM_INCIDENT_INVESTIGATION_STATUSES,
    PARAM_INCIDENT_SEVERITIES,
    PARAM_INCIDENT_USER_STATUSES,
    PARAM_INCIDENT_VERDICTS,
    PARAM_LOOKBACK,
    PARAM_MAX_ALERTS_IN_CASE,
    PARAM_MAX_EVENTS_IN_ALERT,
    PARAM_PYTHON_TIMEOUT,
    PARAM_VERIFY_SSL,
    PYTHON_PROCESS_TIMEOUT_DEFAULT,
    PYTHON_TIMEOUT_MAX,
    PYTHON_TIMEOUT_MIN,
    TEST_RUN_MAX_FETCH,
)
from ..core.IngestionPipeline import IngestionPipeline
from ..core.utils import (
    ConnectorConfig,
    format_test_connection_summary,
    format_user_facing_error,
    parse_int_in_range,
    truthy,
    validate_connector_fields,
)
from ..core.VegaManager import VegaClientConfig, VegaManager

if TYPE_CHECKING:
    from TIPCommon.types import SingleJson


def _connector_id(siemplify: SiemplifyConnectorExecution) -> str:
    """Return the connector instance identifier used for context properties."""
    return str(siemplify.context.connector_info.identifier)


def _read_json(siemplify: SiemplifyConnectorExecution, identifier: str, key: str) -> SingleJson:
    """Load a JSON object from connector context, or {} when missing/invalid."""
    raw = siemplify.get_connector_context_property(identifier=identifier, property_key=key)
    if not raw:
        return {}
    data = json.loads(raw)
    return data if isinstance(data, dict) else {}


def _write_json(
    siemplify: SiemplifyConnectorExecution,
    identifier: str,
    key: str,
    payload: SingleJson,
) -> None:
    """Persist a JSON object to connector context."""
    siemplify.set_connector_context_property(
        identifier=identifier,
        property_key=key,
        property_value=json.dumps(payload or {}),
    )


@contextmanager
def _mute_siemplify_logs(siemplify: SiemplifyConnectorExecution) -> Iterator[None]:
    """Keep test-connection output to the friendly summary or field error."""
    logger = getattr(siemplify, "LOGGER", None)
    if logger is None:
        yield
        return
    names = ("info", "error", "warning", "warn", "debug", "exception")
    original = {name: getattr(logger, name, None) for name in names}

    def _noop(*_args: Any, **_kwargs: Any) -> None:
        return None

    for name, method in original.items():
        if callable(method):
            setattr(logger, name, _noop)
    try:
        yield
    finally:
        for name, method in original.items():
            if method is not None:
                setattr(logger, name, method)


def _clear_captured_output(siemplify: SiemplifyConnectorExecution) -> None:
    """Drop SDK noise (overflow_settings, stack traces) from test output."""
    logger = getattr(siemplify, "LOGGER", None)
    rows = getattr(logger, "_log_rows", None) if logger is not None else None
    if isinstance(rows, list):
        rows.clear()
    stdout = getattr(sys, "stdout", None)
    if stdout is not None and hasattr(stdout, "truncate") and hasattr(stdout, "seek"):
        with suppress(Exception):
            stdout.truncate(0)
            stdout.seek(0)
    stderr = getattr(sys, "stderr", None)
    if stderr is not None and hasattr(stderr, "truncate") and hasattr(stderr, "seek"):
        with suppress(Exception):
            stderr.truncate(0)
            stderr.seek(0)


def _read_params(siemplify: SiemplifyConnectorExecution) -> dict[str, Any]:
    """Read connector configuration parameters into a plain dict."""
    return {
        "api_root": siemplify.extract_connector_param(param_name=PARAM_API_ROOT),
        "access_key_id": siemplify.extract_connector_param(param_name=PARAM_ACCESS_KEY_ID),
        "access_key": siemplify.extract_connector_param(param_name=PARAM_ACCESS_KEY),
        "verify_ssl": siemplify.extract_connector_param(param_name=PARAM_VERIFY_SSL, default_value="true"),
        "lookback_minutes": siemplify.extract_connector_param(param_name=PARAM_LOOKBACK, default_value="5"),
        "backfill_days": siemplify.extract_connector_param(param_name=PARAM_BACKFILL, default_value="30"),
        "max_alerts_in_case": siemplify.extract_connector_param(
            param_name=PARAM_MAX_ALERTS_IN_CASE,
            default_value=str(MAX_ALERTS_IN_CASE_DEFAULT),
        ),
        "max_events_in_alert": siemplify.extract_connector_param(
            param_name=PARAM_MAX_EVENTS_IN_ALERT,
            default_value=str(MAX_EVENTS_PER_ALERT_DEFAULT),
        ),
        "alert_severities": siemplify.extract_connector_param(param_name=PARAM_ALERT_SEVERITIES, default_value=""),
        "alert_statuses": siemplify.extract_connector_param(param_name=PARAM_ALERT_STATUSES, default_value=""),
        "alert_verdicts": siemplify.extract_connector_param(param_name=PARAM_ALERT_VERDICTS, default_value=""),
        "incident_severities": siemplify.extract_connector_param(
            param_name=PARAM_INCIDENT_SEVERITIES, default_value=""
        ),
        "incident_user_statuses": siemplify.extract_connector_param(
            param_name=PARAM_INCIDENT_USER_STATUSES, default_value=""
        ),
        "incident_investigation_statuses": siemplify.extract_connector_param(
            param_name=PARAM_INCIDENT_INVESTIGATION_STATUSES, default_value=""
        ),
        "incident_verdicts": siemplify.extract_connector_param(param_name=PARAM_INCIDENT_VERDICTS, default_value=""),
        "python_timeout": siemplify.extract_connector_param(
            param_name=PARAM_PYTHON_TIMEOUT,
            default_value=PYTHON_PROCESS_TIMEOUT_DEFAULT,
        ),
    }


def _validate_params(params: dict[str, Any]) -> None:
    """Raise when required connector fields fail validation."""
    validate_connector_fields(
        ConnectorConfig(
            api_root=params["api_root"],
            access_key_id=params["access_key_id"],
            access_key=params["access_key"],
            lookback_minutes=params["lookback_minutes"],
            backfill_days=params["backfill_days"],
            alert_severities=params["alert_severities"],
            alert_statuses=params["alert_statuses"],
            alert_verdicts=params["alert_verdicts"],
            incident_severities=params["incident_severities"],
            incident_user_statuses=params["incident_user_statuses"],
            incident_investigation_statuses=params["incident_investigation_statuses"],
            incident_verdicts=params["incident_verdicts"],
            max_events_in_alert=params["max_events_in_alert"],
            max_alerts_in_case=params["max_alerts_in_case"],
            python_timeout=params["python_timeout"],
        )
    )


def _build_manager_and_pipeline(
    siemplify: SiemplifyConnectorExecution,
    params: dict[str, Any],
) -> tuple[VegaManager, IngestionPipeline, int]:
    """Construct VegaManager and IngestionPipeline from connector params."""
    max_alerts = parse_int_in_range(
        params["max_alerts_in_case"],
        PARAM_MAX_ALERTS_IN_CASE,
        MAX_ALERTS_IN_CASE_MIN,
        MAX_ALERTS_IN_CASE_MAX,
        default=MAX_ALERTS_IN_CASE_DEFAULT,
    )
    max_events = parse_int_in_range(
        params["max_events_in_alert"],
        PARAM_MAX_EVENTS_IN_ALERT,
        MAX_EVENTS_PER_ALERT_MIN,
        MAX_EVENTS_PER_ALERT_MAX,
        default=MAX_EVENTS_PER_ALERT_DEFAULT,
    )
    manager = VegaManager(
        VegaClientConfig(
            api_root=params["api_root"],
            access_key_id=params["access_key_id"],
            access_key=params["access_key"],
            verify_ssl=truthy(params.get("verify_ssl", True)),
        ),
        logger_instance=siemplify.LOGGER,
    )
    pipeline = IngestionPipeline(
        manager=manager,
        lookback_minutes=params["lookback_minutes"],
        backfill_days=params["backfill_days"],
        alert_severities=params["alert_severities"],
        alert_statuses=params["alert_statuses"],
        alert_verdicts=params["alert_verdicts"],
        incident_severities=params["incident_severities"],
        incident_user_statuses=params["incident_user_statuses"],
        incident_investigation_statuses=params["incident_investigation_statuses"],
        incident_verdicts=params["incident_verdicts"],
        max_alerts_in_case=max_alerts,
        max_events_in_alert=max_events,
        max_fetch=TEST_RUN_MAX_FETCH if params.get("is_test_run") else None,
        logger_instance=siemplify.LOGGER,
    )
    return manager, pipeline, max_events


def _compute_deadline(python_timeout: Any) -> float:
    """Return a monotonic deadline that leaves buffer before connector timeout."""
    timeout_seconds = parse_int_in_range(
        python_timeout,
        PARAM_PYTHON_TIMEOUT,
        PYTHON_TIMEOUT_MIN,
        PYTHON_TIMEOUT_MAX,
        default=int(PYTHON_PROCESS_TIMEOUT_DEFAULT),
    )
    budget = max(timeout_seconds - INGEST_STOP_BUFFER_SECONDS, 15)
    return time.monotonic() + budget


def _run_test_connection(siemplify: SiemplifyConnectorExecution, params: dict[str, Any]) -> tuple[list[Any], str]:
    """Ping Vega, preview matching records, and return sample AlertInfo packages."""
    _validate_params(params)
    _manager, pipeline, max_events = _build_manager_and_pipeline(siemplify, params)
    _manager.test_connection()
    preview = pipeline.preview()
    alerts = create_alerts(preview.get("records") or [], siemplify, None, max_events_in_alert=max_events)
    summary = format_test_connection_summary(
        incident_count=preview.get("incident_count") or 0,
        related_alert_count=preview.get("related_alert_count") or 0,
        unrelated_alert_count=0,
        total_alert_count=preview.get("total_alert_count") or 0,
        sample_count=len(alerts),
        include_incidents=True,
        include_related=True,
        include_unrelated=False,
    )
    return alerts, summary


def _run_ingest(siemplify: SiemplifyConnectorExecution, params: dict[str, Any]) -> list[Any]:
    """Run one ingest cycle and update the checkpoint."""
    _validate_params(params)
    _manager, pipeline, max_events = _build_manager_and_pipeline(siemplify, params)
    _manager.test_connection()
    checkpoint = _read_json(siemplify, _connector_id(siemplify), CHECKPOINT_PROPERTY_KEY)
    deadline = _compute_deadline(params["python_timeout"])
    summary = pipeline.run(checkpoint=checkpoint, deadline_monotonic=deadline)
    records = summary.get("records") or []
    alerts = create_alerts(records, siemplify, siemplify.LOGGER, max_events_in_alert=max_events)
    siemplify.LOGGER.info(
        f"Step 7 — handing {len(alerts)} signal alert package(s) to SecOps. "
        "Incident fields are maintained by the Sync Alerts job. "
        "SecOps creates/groups cases after this handoff."
    )
    if summary.get("incomplete"):
        siemplify.LOGGER.info(
            "Cycle stopped early to avoid connector timeout; next run resumes "
            f"from watermark {(summary.get('checkpoint') or {}).get('watermark')}."
        )
    _write_json(
        siemplify,
        _connector_id(siemplify),
        CHECKPOINT_PROPERTY_KEY,
        summary.get("checkpoint") or {},
    )
    return alerts


@output_handler
def main(is_test_run: bool) -> None:
    """Run a test preview or a full ingest cycle and return the alert package."""
    siemplify = SiemplifyConnectorExecution()
    siemplify.script_name = CONNECTOR_NAME
    alerts: list[Any] = []
    try:
        if is_test_run:
            with _mute_siemplify_logs(siemplify):
                params = _read_params(siemplify)
                params["is_test_run"] = True
                alerts, summary = _run_test_connection(siemplify, params)
            _clear_captured_output(siemplify)
            siemplify.LOGGER.info(summary)
        else:
            params = _read_params(siemplify)
            params["is_test_run"] = False
            alerts = _run_ingest(siemplify, params)
    except Exception as error:
        message = format_user_facing_error(error)
        if is_test_run:
            _clear_captured_output(siemplify)
            siemplify.LOGGER.error(message)
        else:
            siemplify.LOGGER.error(message)
    siemplify.return_package(alerts)


if __name__ == "__main__":
    is_test_run = not (len(sys.argv) < 2 or sys.argv[1] == "True")
    main(is_test_run)
