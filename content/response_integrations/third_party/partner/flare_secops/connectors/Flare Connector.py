"""
Threat Findings Ingestion connector.

Polls Flare findings → SOAR AlertInfo packages via return_package().
When Auto Remediate is enabled, syncs closed SOAR Flare cases back to Flare
using the SOAR SDK only (no Google service account).
"""
from __future__ import annotations

import json
import sys

from soar_sdk.SiemplifyConnectors import SiemplifyConnectorExecution
from soar_sdk.SiemplifyUtils import output_handler

from ..core.AlertPackager import create_alerts
from ..core.constants import (
    CHECKPOINT_PROPERTY_KEY,
    DEFAULT_FLARE_API_URL,
    INTEGRATION_NAME,
    REMEDIATION_PROPERTY_KEY,
    THREAT_FINDINGS_CONNECTOR_NAME,
    VENDOR_NAME,
)
from ..core.FlareManager import FlareManager
from ..core.IngestionPipeline import IngestionPipeline
from ..core.Remediator import SoarRemediator
from ..core.utils import format_user_facing_error, parse_tenant_id


def _truthy(value) -> bool:
    return str(value or "").strip().lower() in ("true", "1", "yes")


def _checkpoint_id(siemplify: SiemplifyConnectorExecution) -> str:
    identifier = siemplify.context.connector_info.identifier
    return f"flare_ingestion_checkpoint_{identifier}"


def _remediation_id(siemplify: SiemplifyConnectorExecution) -> str:
    identifier = siemplify.context.connector_info.identifier
    return f"flare_remediation_state_{identifier}"


def load_checkpoint(siemplify) -> dict:
    try:
        raw = siemplify.get_connector_context_property(
            identifier=_checkpoint_id(siemplify),
            property_key=CHECKPOINT_PROPERTY_KEY,
        )
        if not raw:
            return {}
        data = json.loads(raw)
        return data if isinstance(data, dict) else {}
    except Exception as exc:
        siemplify.LOGGER.error(
            f"Unable to read ingestion checkpoint: {format_user_facing_error(exc)}"
        )
        return {}


def save_checkpoint(siemplify, checkpoint: dict) -> None:
    try:
        siemplify.set_connector_context_property(
            identifier=_checkpoint_id(siemplify),
            property_key=CHECKPOINT_PROPERTY_KEY,
            property_value=json.dumps(checkpoint or {}),
        )
        siemplify.LOGGER.info("Saved ingestion checkpoint.")
    except Exception as exc:
        siemplify.LOGGER.error(
            f"Failed to store ingestion checkpoint: {format_user_facing_error(exc)}"
        )


def load_remediation_state(siemplify) -> dict:
    try:
        raw = siemplify.get_connector_context_property(
            identifier=_remediation_id(siemplify),
            property_key=REMEDIATION_PROPERTY_KEY,
        )
        if not raw:
            return {"last_successful_check_timestamp": None, "processed_alerts": {}}
        data = json.loads(raw)
        if not isinstance(data, dict):
            return {"last_successful_check_timestamp": None, "processed_alerts": {}}
        data.setdefault("processed_alerts", {})
        return data
    except Exception as exc:
        siemplify.LOGGER.error(
            f"Unable to read remediation state: {format_user_facing_error(exc)}"
        )
        return {"last_successful_check_timestamp": None, "processed_alerts": {}}


def save_remediation_state(siemplify, state: dict) -> None:
    try:
        siemplify.set_connector_context_property(
            identifier=_remediation_id(siemplify),
            property_key=REMEDIATION_PROPERTY_KEY,
            property_value=json.dumps(state or {}),
        )
        siemplify.LOGGER.info("Saved remediation state.")
    except Exception as exc:
        siemplify.LOGGER.error(
            f"Failed to store remediation state: {format_user_facing_error(exc)}"
        )


@output_handler
def main(is_test_run: bool):
    siemplify = SiemplifyConnectorExecution()
    siemplify.script_name = THREAT_FINDINGS_CONNECTOR_NAME

    flare_api_key = siemplify.extract_connector_param(param_name="Flare API Key")
    flare_tenant_id = siemplify.extract_connector_param(param_name="Flare Tenant ID")
    # Empty = fetch all values from Flare filter APIs (case-insensitive resolve).
    severity_filter = siemplify.extract_connector_param(
        param_name="Severity Filter", default_value=""
    )
    source_types_filter = siemplify.extract_connector_param(
        param_name="Source Types Filter", default_value=""
    )
    ingest_full = siemplify.extract_connector_param(
        param_name="Ingest Full Event", default_value="true"
    )
    backfill_range_days = siemplify.extract_connector_param(
        param_name="Backfill Range (Days)", default_value="0"
    )
    auto_remediate = siemplify.extract_connector_param(
        param_name="Auto Remediate", default_value="false"
    )

    if is_test_run:
        siemplify.LOGGER.info("***** This is a test run ******")

    try:
        if not flare_api_key:
            raise Exception(
                "Flare API Key is required. Enter your API key and try again."
            )

        tenant_id = parse_tenant_id(flare_tenant_id)

        flare = FlareManager(
            api_key=flare_api_key,
            tenant_id=tenant_id,
            api_url=DEFAULT_FLARE_API_URL,
            logger_instance=siemplify.LOGGER,
        )
        flare.test_connection()

        checkpoint = {} if is_test_run else load_checkpoint(siemplify)
        pipeline = IngestionPipeline(
            flare_manager=flare,
            tenant_id=tenant_id,
            severity_filter=severity_filter or "",
            source_types_filter=source_types_filter or "",
            ingest_full_event=_truthy(ingest_full),
            backfill_range_days=str(backfill_range_days or "0"),
            max_events=5 if is_test_run else None,
            logger_instance=siemplify.LOGGER,
        )
        summary = pipeline.run(checkpoint=checkpoint)
        siemplify.LOGGER.info(summary.get("message"))

        alerts = create_alerts(
            summary.get("findings") or [],
            siemplify,
            tenant_id=tenant_id,
            logger_instance=siemplify.LOGGER,
        )

        if not is_test_run:
            save_checkpoint(siemplify, summary.get("checkpoint") or {})

        if _truthy(auto_remediate) and not is_test_run:
            rem_state = load_remediation_state(siemplify)
            remediator = SoarRemediator(
                flare_manager=flare,
                siemplify=siemplify,
                rule_generator=VENDOR_NAME,
                state=rem_state,
                logger_instance=siemplify.LOGGER,
            )
            rem_result = remediator.run_once()
            siemplify.LOGGER.info(rem_result.get("message"))
            if rem_result.get("state"):
                save_remediation_state(siemplify, rem_result["state"])

        siemplify.LOGGER.info(
            "------------------- Main - Finished "
            f"(fetched={summary.get('fetched')}, alerts={len(alerts)}) -------------------"
        )
        siemplify.return_package(alerts)

    except Exception as error:
        friendly = format_user_facing_error(error)
        siemplify.LOGGER.error(
            f"Failed to run {INTEGRATION_NAME} connector! Error: {friendly}"
        )
        # "from None" drops the SDK/HTTP traceback chain so the Testing tab and
        # Logs show only the operator-facing sentence.
        raise Exception(friendly) from None


if __name__ == "__main__":
    is_test_run = not (len(sys.argv) < 2 or sys.argv[1] == "True")
    main(is_test_run)
