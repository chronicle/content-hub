from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from ..core.GoogleChatManager import GoogleChatManager
from TIPCommon import extract_configuration_param
from ..core.constants import PING_SCRIPT_NAME, INTEGRATION_NAME


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = PING_SCRIPT_NAME
    siemplify.LOGGER.info("================= Main - Param Init =================")

    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Root URL",
        is_mandatory=True,
    )
    service_account = extract_configuration_param(
        siemplify, provider_name=INTEGRATION_NAME, param_name="Service Account"
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        print_value=True,
        input_type=bool,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    try:
        GoogleChatManager(
            api_root=api_root,
            service_account_string=service_account,
            verify_ssl=verify_ssl,
            force_check_connectivity=True,
        )
        status = EXECUTION_STATE_COMPLETED
        output_message = "Successfully connected to the Google Chat with the provided connection parameters!"
        result_value = True

    except Exception as e:
        output_message = f"Failed to connect to the {INTEGRATION_NAME}. Error is {e}"
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        result_value = False

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}:")
    siemplify.LOGGER.info(f"Result Value: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
