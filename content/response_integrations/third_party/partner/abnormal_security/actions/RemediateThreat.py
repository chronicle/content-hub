"""Remediate Threat action for Abnormal Security Google SecOps SOAR Integration."""

from __future__ import annotations

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from TIPCommon.extraction import extract_action_param, extract_configuration_param

from ..core.AbnormalManager import (
    AbnormalAuthenticationError,
    AbnormalConnectionError,
    AbnormalManager,
    AbnormalValidationError,
)
from ..core.constants import INTEGRATION_NAME, REMEDIATE_THREAT_SCRIPT_NAME


@output_handler
def main() -> None:
    """Main execution logic for the Remediate Threat action."""
    siemplify = SiemplifyAction()
    siemplify.script_name = REMEDIATE_THREAT_SCRIPT_NAME
    siemplify.LOGGER.info(f"Action: {REMEDIATE_THREAT_SCRIPT_NAME} started")

    api_url = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API URL",
        is_mandatory=True,
        print_value=True,
    )
    api_key = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Key",
        is_mandatory=True,
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        input_type=bool,
        is_mandatory=False,
        default_value=True,
    )

    threat_id = extract_action_param(
        siemplify,
        param_name="Threat ID",
        is_mandatory=True,
        print_value=True,
    )
    message_ids_raw = extract_action_param(
        siemplify, param_name="Message IDs", is_mandatory=False
    )
    message_ids = (
        [m.strip() for m in message_ids_raw.split(",") if m.strip()]
        if message_ids_raw
        else None
    )

    result_value = False
    status = EXECUTION_STATE_FAILED
    try:
        manager = AbnormalManager(api_url=api_url, api_key=api_key, verify_ssl=verify_ssl)
        response = manager.post_threat_action(
            threat_id=threat_id,
            action="remediate",
            message_ids=message_ids,
        )
        siemplify.result.add_result_json(response)
        output_message = f"Remediate request submitted for threat {threat_id}."
        result_value = True
        status = EXECUTION_STATE_COMPLETED

    except (
        AbnormalValidationError,
        AbnormalAuthenticationError,
        AbnormalConnectionError,
        Exception,
    ) as e:
        output_message = (
            f'Error executing action "{REMEDIATE_THREAT_SCRIPT_NAME}". Reason: {e}'
        )
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}  Result: {result_value}")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
