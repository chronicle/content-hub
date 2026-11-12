"""
Vega Alerts and Incidents Connector.

1. Read connector configuration (API, entities, filters, Has Related Incidents).
2. IngestionPipeline applies those filters:
   - Incidents+Alerts+Yes: one incident-only case, plus related Vega alerts
     that share one source grouping identifier. SecOps groups them up to
     the tenant maxAlertsInCase.
   - Incidents+Alerts+No: incident-only case plus standalone unrelated alerts.
   - Incidents only: Vega Incident cases only (no related or unrelated alerts).
   - Alerts+Yes: one case per related Vega alert (no incident case).
   - Alerts+No: one case per unrelated Vega alert.
   Each packaged record is a SOAR alert inside its case.
3. Packager turns records into SOAR AlertInfo objects. Optional outbound
   sync sets Vega userStatus to RESOLVED when the matching SOAR case closes
   (incident case → incident only; related-alert or alert case → those alerts only).
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
    PARAM_ACCESS_KEY,
    PARAM_ACCESS_KEY_ID,
    PARAM_ALERT_SEVERITIES,
    PARAM_ALERT_STATUSES,
    PARAM_ALERT_VERDICTS,
    PARAM_API_ROOT,
    PARAM_BACKFILL,
    PARAM_ENTITIES,
    PARAM_FETCH_RELATED_ALERT_METADATA,
    PARAM_HAS_RELATED,
    PARAM_INCIDENT_INVESTIGATION_STATUSES,
    PARAM_INCIDENT_SEVERITIES,
    PARAM_INCIDENT_USER_STATUSES,
    PARAM_INCIDENT_VERDICTS,
    PARAM_LOOKBACK,
    PARAM_PYTHON_TIMEOUT,
    PARAM_SYNC,
    PARAM_VERIFY_SSL,
    PYTHON_PROCESS_TIMEOUT_DEFAULT,
    PYTHON_TIMEOUT_MAX,
    PYTHON_TIMEOUT_MIN,
    REMEDIATION_PROPERTY_KEY,
    TEST_RUN_MAX_FETCH,
)
from ..core.IngestionPipeline import IngestionPipeline
from ..core.Remediator import SoarRemediator, ingest_skip_ids, ingest_sync_refs
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
        "entities_raw": siemplify.extract_connector_param(param_name=PARAM_ENTITIES, default_value="Alerts,Incidents"),
        "lookback_minutes": siemplify.extract_connector_param(param_name=PARAM_LOOKBACK, default_value="5"),
        "backfill_days": siemplify.extract_connector_param(param_name=PARAM_BACKFILL, default_value="30"),
        "alert_severities": siemplify.extract_connector_param(param_name=PARAM_ALERT_SEVERITIES, default_value=""),
        "alert_statuses": siemplify.extract_connector_param(param_name=PARAM_ALERT_STATUSES, default_value=""),
        "alert_verdicts": siemplify.extract_connector_param(param_name=PARAM_ALERT_VERDICTS, default_value=""),
        "has_related": siemplify.extract_connector_param(param_name=PARAM_HAS_RELATED, default_value="Yes,No"),
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
        "fetch_related_alert_metadata": siemplify.extract_connector_param(
            param_name=PARAM_FETCH_RELATED_ALERT_METADATA, default_value="false"
        ),
        "sync_close": siemplify.extract_connector_param(param_name=PARAM_SYNC, default_value="true"),
    }


def _validate_params(params: dict[str, Any]) -> None:
    """Raise when required connector fields fail validation."""
    validate_connector_fields(
        ConnectorConfig(
            api_root=params["api_root"],
            access_key_id=params["access_key_id"],
            access_key=params["access_key"],
            entities_raw=params["entities_raw"],
            lookback_minutes=params["lookback_minutes"],
            backfill_days=params["backfill_days"],
            alert_severities=params["alert_severities"],
            alert_statuses=params["alert_statuses"],
            alert_verdicts=params["alert_verdicts"],
            has_related=params["has_related"],
            incident_severities=params["incident_severities"],
            incident_user_statuses=params["incident_user_statuses"],
            incident_investigation_statuses=params["incident_investigation_statuses"],
            incident_verdicts=params["incident_verdicts"],
            python_timeout=params["python_timeout"],
        )
    )


def _build_manager_and_pipeline(
    siemplify: SiemplifyConnectorExecution,
    params: dict[str, Any],
) -> tuple[VegaManager, IngestionPipeline]:
    """Construct VegaManager and IngestionPipeline from connector params."""
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
        entities_raw=params["entities_raw"],
        lookback_minutes=params["lookback_minutes"],
        backfill_days=params["backfill_days"],
        alert_severities=params["alert_severities"],
        alert_statuses=params["alert_statuses"],
        alert_verdicts=params["alert_verdicts"],
        has_related=params["has_related"],
        incident_severities=params["incident_severities"],
        incident_user_statuses=params["incident_user_statuses"],
        incident_investigation_statuses=params["incident_investigation_statuses"],
        incident_verdicts=params["incident_verdicts"],
        fetch_related_alert_metadata=truthy(params.get("fetch_related_alert_metadata")),
        max_fetch=TEST_RUN_MAX_FETCH if params.get("is_test_run") else None,
        logger_instance=siemplify.LOGGER,
    )
    return manager, pipeline


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


def _run_close_sync(
    siemplify: SiemplifyConnectorExecution,
    manager: VegaManager,
    records: list[tuple[str, SingleJson]],
) -> None:
    """Resolve matching Vega entities when tracked SOAR cases have closed."""
    rem_state = _read_json(siemplify, _connector_id(siemplify), REMEDIATION_PROPERTY_KEY)
    remediator = SoarRemediator(
        manager=manager,
        siemplify=siemplify,
        logger_instance=siemplify.LOGGER,
    )
    rem_result = remediator.run_once(
        rem_state,
        skip_ids=ingest_skip_ids(records),
        ingest_refs=ingest_sync_refs(records),
    )
    if rem_result.get("message"):
        siemplify.LOGGER.info(rem_result["message"])
    if rem_result.get("state"):
        _write_json(
            siemplify,
            _connector_id(siemplify),
            REMEDIATION_PROPERTY_KEY,
            rem_result["state"],
        )


def _run_test_connection(siemplify: SiemplifyConnectorExecution, params: dict[str, Any]) -> tuple[list[Any], str]:
    """Ping Vega, preview matching records, and return sample AlertInfo packages."""
    _validate_params(params)
    manager, pipeline = _build_manager_and_pipeline(siemplify, params)
    manager.test_connection()
    preview = pipeline.preview()
    alerts = create_alerts(preview.get("records") or [], siemplify, None)
    summary = format_test_connection_summary(
        incident_count=preview.get("incident_count") or 0,
        related_alert_count=preview.get("related_alert_count") or 0,
        unrelated_alert_count=preview.get("unrelated_alert_count") or 0,
        total_alert_count=preview.get("total_alert_count") or 0,
        sample_count=len(alerts),
        include_incidents=bool(preview.get("include_incidents")),
        include_related=bool(preview.get("include_related")),
        include_unrelated=bool(preview.get("include_unrelated")),
    )
    return alerts, summary


def _run_ingest(siemplify: SiemplifyConnectorExecution, params: dict[str, Any]) -> list[Any]:
    """Run one ingest cycle, update checkpoint, and optionally close-sync to Vega."""
    _validate_params(params)
    manager, pipeline = _build_manager_and_pipeline(siemplify, params)
    manager.test_connection()
    checkpoint = _read_json(siemplify, _connector_id(siemplify), CHECKPOINT_PROPERTY_KEY)
    deadline = _compute_deadline(params["python_timeout"])
    summary = pipeline.run(checkpoint=checkpoint, deadline_monotonic=deadline)
    records = summary.get("records") or []
    alerts = create_alerts(records, siemplify, siemplify.LOGGER)
    incident_packages = sum(1 for kind, _record in records if kind == "Incident")
    alert_packages = sum(1 for kind, _record in records if kind == "Alert")
    siemplify.LOGGER.info(
        f"Step 7 — handing {len(alerts)} alert package(s) to SecOps "
        f"({incident_packages} incident, {alert_packages} alert). "
        "This is the full list. The connector does not trim it to 250. "
        "SecOps creates the cases after this handoff. "
        f"If the case queue total is lower than {len(alerts)}, SecOps kept "
        "fewer packages than this run returned."
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
    if (not summary.get("incomplete")) and truthy(params.get("sync_close")):
        _run_close_sync(siemplify, manager, records)
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
