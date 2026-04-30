"""
Ping action for Abnormal Security Google SecOps SOAR Integration.

Tests connectivity and authentication to the Abnormal Security API.
"""

from __future__ import annotations

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from TIPCommon import extract_configuration_param

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
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = PING_SCRIPT_NAME
    siemplify.LOGGER.info(f"Action: {PING_SCRIPT_NAME} started")

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
        print_value=True,
    )

    result_value = False
    status = EXECUTION_STATE_FAILED
    output_message = ""

    try:
        manager = AbnormalManager(api_url=api_url, api_key=api_key, verify_ssl=verify_ssl)
        manager.test_connectivity()

        output_message = (
            f"Successfully connected to the {INTEGRATION_DISPLAY_NAME} API at {api_url}."
        )
        result_value = True
        status = EXECUTION_STATE_COMPLETED
        siemplify.LOGGER.info(output_message)

    except AbnormalAuthenticationError as e:
        output_message = (
            f"Failed to connect to the {INTEGRATION_DISPLAY_NAME} server! "
            f"Authentication failed — please verify the API key. Error: {e}"
        )
        siemplify.LOGGER.error(output_message)

    except AbnormalConnectionError as e:
        output_message = (
            f"Failed to connect to the {INTEGRATION_DISPLAY_NAME} server! "
            f"Cannot reach {api_url} — check the URL and network. Error: {e}"
        )
        siemplify.LOGGER.error(output_message)

    except Exception as e:
        output_message = (
            f"Failed to connect to the {INTEGRATION_DISPLAY_NAME} server! "
            f"An unexpected error occurred: {e}"
        )
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}  Result: {result_value}")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
