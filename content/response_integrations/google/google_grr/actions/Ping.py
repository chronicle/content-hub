from __future__ import annotations
from TIPCommon import extract_configuration_param

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from ..core.GoogleGRRManager import GoogleGRRManager
from ..core.consts import INTEGRATION_NAME, INTEGRATION_DISPLAY_NAME

SCRIPT_NAME = "Ping"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = f"{INTEGRATION_NAME} - {SCRIPT_NAME}"
    siemplify.LOGGER.info("================= Main - Param Init =================")

    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Root",
        is_mandatory=True,
        print_value=True,
    )

    username = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Username",
        is_mandatory=True,
        print_value=True,
    )

    password = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Password",
        is_mandatory=True,
    )

    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        input_type=bool,
        is_mandatory=False,
        print_value=True,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    try:
        manager = GoogleGRRManager(
            api_root=api_root,
            username=username,
            password=password,
            verify_ssl=verify_ssl,
        )

        siemplify.LOGGER.info(f"Connecting to {INTEGRATION_DISPLAY_NAME}")
        manager.test_connectivity()
        siemplify.LOGGER.info(
            f"Successfully connected to the {INTEGRATION_DISPLAY_NAME} server with the provided "
            f"connection parameters!"
        )

        result_value = "true"
        status = EXECUTION_STATE_COMPLETED
        output_message = f"Successfully connected to {INTEGRATION_DISPLAY_NAME}"

    except Exception as error:
        result_value = "false"
        status = EXECUTION_STATE_FAILED
        output_message = f"Failed to connect to the {INTEGRATION_DISPLAY_NAME} server! Error is {error}"
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(error)

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}:")
    siemplify.LOGGER.info(f"Result Value: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
