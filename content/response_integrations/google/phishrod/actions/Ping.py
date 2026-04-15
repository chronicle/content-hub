from __future__ import annotations
from ..core.PhishrodManager import PhishrodManager

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from TIPCommon.extraction import extract_configuration_param
from ..core.constants import INTEGRATION_NAME, INTEGRATION_DISPLAY_NAME, PING_SCRIPT_NAME


@output_handler
def main() -> None:
    siemplify = SiemplifyAction()
    siemplify.script_name = PING_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Root",
        is_mandatory=True,
        print_value=True,
    )
    api_key = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Key",
        is_mandatory=True,
        remove_whitespaces=False,
    )
    client_id = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Client ID",
        is_mandatory=True,
        print_value=False,
        remove_whitespaces=False,
    )
    username = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Username",
        is_mandatory=True,
        print_value=True,
        remove_whitespaces=True,
    )
    password = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Password",
        is_mandatory=True,
        print_value=False,
        remove_whitespaces=False,
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        is_mandatory=True,
        input_type=bool,
        print_value=True,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    try:
        manager = PhishrodManager(
            api_root=api_root,
            api_key=api_key,
            client_id=client_id,
            username=username,
            password=password,
            verify_ssl=verify_ssl,
            siemplify_logger=siemplify.LOGGER,
        )
        manager.test_connectivity()
        result = True
        status = EXECUTION_STATE_COMPLETED
        output_message = (
            f"Successfully connected to the {INTEGRATION_DISPLAY_NAME} server with the provided "
            f"connection parameters!"
        )

    except Exception as error:
        siemplify.LOGGER.error(f"General error performing action {PING_SCRIPT_NAME}")
        siemplify.LOGGER.exception(error)
        result = False
        status = EXECUTION_STATE_FAILED
        output_message = f"Failed to connect to the {INTEGRATION_DISPLAY_NAME} server! Error is {error}"

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"Result: {result}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")

    siemplify.end(output_message, result, status)


if __name__ == "__main__":
    main()
