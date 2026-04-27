from __future__ import annotations
from TIPCommon import extract_configuration_param

from ..core.DevoManager import DevoManager
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from ..core.consts import INTEGRATION_IDENTIFIER, INTEGRATION_DISPLAY_NAME, PING_SCRIPT_NAME


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = f"{INTEGRATION_IDENTIFIER} - {PING_SCRIPT_NAME}"
    siemplify.LOGGER.info("=================== Main - Param Init ===================")

    # Integration configuration
    api_url = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_IDENTIFIER,
        param_name="API URL",
        is_mandatory=True,
        print_value=True,
    )
    api_token = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_IDENTIFIER,
        param_name="API Token",
        is_mandatory=False,
        print_value=False,
        remove_whitespaces=False,
    )
    api_key = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_IDENTIFIER,
        param_name="API Key",
        is_mandatory=False,
        print_value=False,
        remove_whitespaces=False,
    )
    api_secret = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_IDENTIFIER,
        param_name="API Secret",
        is_mandatory=False,
        print_value=False,
        remove_whitespaces=False,
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_IDENTIFIER,
        param_name="Verify SSL",
        input_type=bool,
        is_mandatory=True,
        default_value=True,
        print_value=True,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    try:
        DevoManager(
            api_url=api_url,
            api_token=api_token,
            api_key=api_key,
            api_secret=api_secret,
            verify_ssl=verify_ssl,
            force_test_connectivity=True,
            siemplify=siemplify,
        )
        status = EXECUTION_STATE_COMPLETED
        output_message = (
            f"Successfully connected to the {INTEGRATION_DISPLAY_NAME} instance with the provided "
            f"connection parameters!"
        )
        result_value = True

    except Exception as error:
        output_message = f"Failed to connect to the {INTEGRATION_DISPLAY_NAME} instance! Error is: {error}"
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(error)
        status = EXECUTION_STATE_FAILED
        result_value = False

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"Result Value: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
