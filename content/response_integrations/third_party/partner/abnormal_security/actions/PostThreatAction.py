"""Post Threat Action for Abnormal Security Google SecOps SOAR Integration.

Supports single-target invocation (Threat ID parameter) and multi-entity
batch execution when the action is scoped to ThreatSignature entities and
multiple are selected from the case view.
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
from ..core.constants import INTEGRATION_NAME, POST_THREAT_ACTION_SCRIPT_NAME


@output_handler
def main() -> None:
    """Main execution logic for the Post Threat Action."""
    siemplify = SiemplifyAction()
    siemplify.script_name = POST_THREAT_ACTION_SCRIPT_NAME
    siemplify.LOGGER.info(f"Action: {POST_THREAT_ACTION_SCRIPT_NAME} started")

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
    action = siemplify.extract_action_param(
        param_name="Action",
        is_mandatory=True,
        print_value=True,
    )
    message_ids_raw = siemplify.extract_action_param(
        param_name="Message IDs",
        is_mandatory=False,
    )
    message_ids = [m.strip() for m in message_ids_raw.split(",") if m.strip()] if message_ids_raw else None

    # Build the list of threat IDs to act on.
    # 1) If scoped to entities, iterate over target_entities (multi-entity batch).
    # 2) Otherwise fall back to the Threat ID parameter.
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
                response = manager.post_threat_action(
                    threat_id=tid,
                    action=action,
                    message_ids=message_ids,
                )
                successes.append(tid)
                aggregated[tid] = response
            except Exception as inner:
                failures.append((tid, str(inner)))
                siemplify.LOGGER.error(f"Threat {tid} action failed: {inner}")

        siemplify.result.add_result_json(aggregated)
        if successes and not failures:
            output_message = (
                f"Successfully applied action '{action}' to {len(successes)} threat(s): {', '.join(successes)}."
            )
            result_value = True
            status = EXECUTION_STATE_COMPLETED
        elif successes and failures:
            output_message = (
                f"Action '{action}' applied to {len(successes)} threat(s) but "
                f"failed for {len(failures)}: " + "; ".join(f"{t}: {e}" for t, e in failures)
            )
            result_value = True
            status = EXECUTION_STATE_COMPLETED
        else:
            output_message = f"Failed to apply action '{action}' to all {len(failures)} threat(s): " + "; ".join(
                f"{t}: {e}" for t, e in failures
            )

    except (
        AbnormalValidationError,
        AbnormalAuthenticationError,
        AbnormalConnectionError,
        Exception,
    ) as e:
        output_message = f'Error executing action "{POST_THREAT_ACTION_SCRIPT_NAME}". Reason: {e}'
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}  Result: {result_value}")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
