"""Get Threat Links action for Abnormal Security Google SecOps SOAR Integration."""

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
from ..core.constants import GET_THREAT_LINKS_SCRIPT_NAME, INTEGRATION_NAME


@output_handler
def main() -> None:
    """Main execution logic for the Get Threat Links action."""
    siemplify = SiemplifyAction()
    siemplify.script_name = GET_THREAT_LINKS_SCRIPT_NAME
    siemplify.LOGGER.info(f"Action: {GET_THREAT_LINKS_SCRIPT_NAME} started")

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

    threat_id = siemplify.extract_action_param(
        param_name="Threat ID",
        is_mandatory=True,
        print_value=True,
    )

    result_value = False
    status = EXECUTION_STATE_FAILED
    try:
        manager = AbnormalManager(api_url=api_url, api_key=api_key, verify_ssl=verify_ssl)
        response = manager.get_threat_links(threat_id=threat_id)
        siemplify.result.add_result_json(response)
        output_message = f"Successfully retrieved links for threat {threat_id}."
        result_value = True
        status = EXECUTION_STATE_COMPLETED

    except (
        AbnormalValidationError,
        AbnormalAuthenticationError,
        AbnormalConnectionError,
        Exception,
    ) as e:
        output_message = f'Error executing action "{GET_THREAT_LINKS_SCRIPT_NAME}". Reason: {e}'
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}  Result: {result_value}")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
