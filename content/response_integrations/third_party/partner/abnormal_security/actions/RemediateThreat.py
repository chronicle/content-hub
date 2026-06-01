"""RemediateThreat action for Abnormal Security Google SecOps SOAR Integration.

Supports single-target invocation (Threat ID parameter) and multi-entity
batch execution when scoped to ThreatSignature entities.
"""

from __future__ import annotations

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

from ..core.AbnormalManager import (
    AbnormalAuthenticationError,
    AbnormalConnectionError,
    AbnormalManager,
    AbnormalValidationError,
)
from ..core.constants import INTEGRATION_NAME, REMEDIATE_THREAT_SCRIPT_NAME


@output_handler
def main() -> None:
    """Main execution logic for the RemediateThreat action."""
    siemplify = SiemplifyAction()
    siemplify.script_name = REMEDIATE_THREAT_SCRIPT_NAME
    siemplify.LOGGER.info(f"Action: {REMEDIATE_THREAT_SCRIPT_NAME} started")

    api_url = siemplify.extract_configuration_param(
        provider_name=INTEGRATION_NAME,
        param_name="API URL",
        is_mandatory=True,
        print_value=True,
    )
    api_key = siemplify.extract_configuration_param(
        provider_name=INTEGRATION_NAME,
        param_name="API Key",
        is_mandatory=True,
    )
    verify_ssl = siemplify.extract_configuration_param(
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        input_type=bool,
        is_mandatory=False,
        default_value=True,
    )
    threat_id_param = siemplify.extract_action_param(
        param_name="Threat ID",
        is_mandatory=False,
        print_value=True,
    )
    message_ids_raw = siemplify.extract_action_param(
        param_name="Message IDs",
        is_mandatory=False,
    )
    message_ids = [m.strip() for m in message_ids_raw.split(",") if m.strip()] if message_ids_raw else None

    _all_entities = getattr(siemplify, "target_entities", None) or []
    target_entities = [e for e in _all_entities if str(getattr(e, "entity_type", "")).upper() == "THREATSIGNATURE"]
    threat_ids: list[str] = []
    if target_entities:
        for entity in target_entities:
            ident = getattr(entity, "identifier", "")
            if ident:
                threat_ids.append(ident)
    elif threat_id_param:
        threat_ids.append(threat_id_param)

    result_value = False
    status = EXECUTION_STATE_FAILED
    successes: list[str] = []
    failures: list[tuple[str, str]] = []
    aggregated: dict[str, dict] = {}

    try:
        if not threat_ids:
            raise AbnormalValidationError(
                "No threat IDs provided. Pass a Threat ID or run on ThreatSignature entities."
            )

        manager = AbnormalManager(api_url=api_url, api_key=api_key, verify_ssl=verify_ssl)
        for tid in threat_ids:
            try:
                response = manager.post_threat_action(threat_id=tid, action="remediate", message_ids=message_ids)
                successes.append(tid)
                aggregated[tid] = response
            except Exception as inner:
                failures.append((tid, str(inner)))
                siemplify.LOGGER.error(f"Threat {tid} remediate failed: {inner}")

        siemplify.result.add_result_json(aggregated)
        if successes and not failures:
            output_message = (
                f"Successfully remediated threats on the following entities using Abnormal Security: "
                f"{', '.join(successes)}"
            )
            result_value = True
            status = EXECUTION_STATE_COMPLETED
        elif successes and failures:
            failed_ids = ", ".join(t for t, _ in failures)
            output_message = (
                f"Successfully remediated threats on the following entities using Abnormal Security: "
                f"{', '.join(successes)}. "
                f"Action wasn't able to remediate threats on the following entities using Abnormal Security: "
                f"{failed_ids}"
            )
            result_value = True
            status = EXECUTION_STATE_COMPLETED
        else:
            failed_ids = ", ".join(t for t, _ in failures)
            output_message = (
                f"Action wasn't able to remediate threats on the following entities using Abnormal Security: "
                f"{failed_ids}"
            )

    except (
        AbnormalValidationError,
        AbnormalAuthenticationError,
        AbnormalConnectionError,
        Exception,
    ) as e:
        output_message = f'Error executing action "{REMEDIATE_THREAT_SCRIPT_NAME}". Reason: {e}'
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}  Result: {result_value}")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
