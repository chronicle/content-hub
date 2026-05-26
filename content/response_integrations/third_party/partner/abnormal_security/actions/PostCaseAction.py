"""Post Case Action for Abnormal Security Google SecOps SOAR Integration.

Supports single-target invocation (Case ID parameter) and multi-entity batch
execution when the action is scoped to ThreatCampaign entities and multiple
are selected from the case view.
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
from ..core.constants import INTEGRATION_NAME, POST_CASE_ACTION_SCRIPT_NAME


@output_handler
def main() -> None:
    """Main execution logic for the Post Case Action."""
    siemplify = SiemplifyAction()
    siemplify.script_name = POST_CASE_ACTION_SCRIPT_NAME
    siemplify.LOGGER.info(f"Action: {POST_CASE_ACTION_SCRIPT_NAME} started")

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
    case_id_param = siemplify.extract_action_param(
        param_name="Case ID",
        is_mandatory=False,
        print_value=True,
    )
    action = siemplify.extract_action_param(
        param_name="Action",
        is_mandatory=True,
        print_value=True,
    )

    _all_entities = getattr(siemplify, "target_entities", None) or []
    target_entities = [e for e in _all_entities if str(getattr(e, "entity_type", "")).upper() == "THREATCAMPAIGN"]
    case_ids: list[str] = []
    if target_entities:
        for entity in target_entities:
            ident = getattr(entity, "identifier", "")
            if ident:
                case_ids.append(ident)
    elif case_id_param:
        case_ids.append(case_id_param)

    result_value = False
    status = EXECUTION_STATE_FAILED
    successes: list[str] = []
    failures: list[tuple[str, str]] = []
    aggregated: dict[str, dict] = {}

    try:
        if not case_ids:
            raise AbnormalValidationError("No case IDs provided. Pass a Case ID or run on ThreatCampaign entities.")

        manager = AbnormalManager(api_url=api_url, api_key=api_key, verify_ssl=verify_ssl)
        for cid in case_ids:
            try:
                response = manager.post_case_action(case_id=cid, action=action)
                successes.append(cid)
                aggregated[cid] = response
            except Exception as inner:
                failures.append((cid, str(inner)))
                siemplify.LOGGER.error(f"Case {cid} action failed: {inner}")

        siemplify.result.add_result_json(aggregated)
        if successes and not failures:
            output_message = (
                f"Successfully applied action '{action}' to {len(successes)} case(s): {', '.join(successes)}."
            )
            result_value = True
            status = EXECUTION_STATE_COMPLETED
        elif successes and failures:
            output_message = (
                f"Action '{action}' applied to {len(successes)} case(s) but "
                f"failed for {len(failures)}: " + "; ".join(f"{c}: {e}" for c, e in failures)
            )
            result_value = True
            status = EXECUTION_STATE_COMPLETED
        else:
            output_message = f"Failed to apply action '{action}' to all {len(failures)} case(s): " + "; ".join(
                f"{c}: {e}" for c, e in failures
            )

    except (
        AbnormalValidationError,
        AbnormalAuthenticationError,
        AbnormalConnectionError,
        Exception,
    ) as e:
        output_message = f'Error executing action "{POST_CASE_ACTION_SCRIPT_NAME}". Reason: {e}'
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}  Result: {result_value}")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
