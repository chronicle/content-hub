from __future__ import annotations

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

from ..core.houdin import HoudinManager
from ..core.houdin_constants import INTEGRATION_NAME, PING_SCRIPT_NAME


@output_handler
def main() -> None:
    siemplify = SiemplifyAction()
    siemplify.script_name = PING_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    api_key = siemplify.extract_configuration_param(INTEGRATION_NAME, param_name="API Key")
    verify_ssl = siemplify.extract_configuration_param(
        INTEGRATION_NAME, param_name="Verify SSL", default_value=True, input_type=bool
    )

    try:
        HoudinManager(api_key, verify_ssl).ping()
        status = EXECUTION_STATE_COMPLETED
        result_value = "true"
        output_message = "Successfully connected to the Houdin.io API with the provided API key."
    except Exception as error:
        siemplify.LOGGER.error(f"Ping failed: {error}")
        siemplify.LOGGER.exception(error)
        status = EXECUTION_STATE_FAILED
        result_value = "false"
        output_message = f"Failed to connect to the Houdin.io API. Error is {error}"

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"status: {status}, result_value: {result_value}, output_message: {output_message}")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
