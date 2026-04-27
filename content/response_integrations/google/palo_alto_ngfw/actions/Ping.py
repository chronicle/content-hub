from __future__ import annotations
import requests

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

from TIPCommon import extract_configuration_param

from ..core.constants import INTEGRATION_NAME, PING_SCRIPT_NAME
from ..core.exceptions import NGFWException
from ..core.NGFWManager import NGFWManager


@output_handler
def main():

    siemplify = SiemplifyAction()
    siemplify.script_name = PING_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Api Root",
        print_value=True,
    )
    username = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Username",
        print_value=False,
    )
    password = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Password",
        print_value=False,
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        input_type=bool,
        print_value=True,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    try:
        NGFWManager(
            server_address=api_root,
            username=username,
            password=password,
            backup_folder=siemplify.run_folder,
            verify_ssl=verify_ssl,
        )

        output_message = f"Successfully connected to {api_root}"
        result_value = True
        status = EXECUTION_STATE_COMPLETED

    except (NGFWException, requests.exceptions.RequestException) as error:
        siemplify.LOGGER.exception(error)
        output_message = (
            f"Error executing action {siemplify.script_name}. Reason: {error}"
        )
        result_value = False
        status = EXECUTION_STATE_FAILED

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"Result: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")

    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
