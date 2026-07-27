"""
Ping action for Abnormal Security Google SecOps SOAR Integration.

Tests connectivity and authentication to the Abnormal Security API.
"""

from __future__ import annotations

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

from ..core.AbnormalManager import (
    AbnormalAuthenticationError,
    AbnormalConnectionError,
    AbnormalManager,
)
from ..core.constants import (
    INTEGRATION_DISPLAY_NAME,
    INTEGRATION_NAME,
    PING_SCRIPT_NAME,
)


@output_handler
def main() -> None:
    """Main execution logic for the Ping action."""
    siemplify = SiemplifyAction()
    siemplify.script_name = PING_SCRIPT_NAME
    siemplify.LOGGER.info(f"Action: {PING_SCRIPT_NAME} started")

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
        print_value=True,
    )

    result_value = False
    status = EXECUTION_STATE_FAILED

    try:
        manager = AbnormalManager(api_url=api_url, api_key=api_key, verify_ssl=verify_ssl)
        manager.test_connectivity()

        output_message = (
            f"Successfully connected to the {INTEGRATION_DISPLAY_NAME} server with the provided connection parameters!"
        )
        result_value = True
        status = EXECUTION_STATE_COMPLETED
        siemplify.LOGGER.info(output_message)

    except (AbnormalAuthenticationError, AbnormalConnectionError, Exception) as e:
        output_message = f"Failed to connect to the {INTEGRATION_DISPLAY_NAME} server! Error is {e}"
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}  Result: {result_value}")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
