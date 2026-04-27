from __future__ import annotations
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyAction import SiemplifyAction
from ..core.AnomaliManager import AnomaliManager
from ..core.constants import INTEGRATION_NAME, PING_SCRIPT_NAME
from TIPCommon import extract_configuration_param


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = PING_SCRIPT_NAME

    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    api_root = extract_configuration_param(
        siemplify, provider_name=INTEGRATION_NAME, param_name="Api Root"
    )
    username = extract_configuration_param(
        siemplify, provider_name=INTEGRATION_NAME, param_name="Username"
    )
    api_key = extract_configuration_param(
        siemplify, provider_name=INTEGRATION_NAME, param_name="Api Key"
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    result_value = True
    output_message = "Connected successfully."
    status = EXECUTION_STATE_COMPLETED

    try:
        AnomaliManager(
            api_root=api_root,
            username=username,
            api_key=api_key,
            force_check_connectivity=True,
        )
    except Exception as e:
        output_message = f"Error executing action '{PING_SCRIPT_NAME}'. Reason: {e}"
        status = EXECUTION_STATE_FAILED
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
        result_value = False

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  success: {result_value}\n  output_message: {output_message}"
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
