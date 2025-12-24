from __future__ import annotations

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

from ..core.PerimeterXManager import PerimeterXManager, PerimeterXManagerException

INTEGRATION_NAME = "PerimeterX"

SCRIPT_NAME = "Ping"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    param_slack_api_key = siemplify.extract_configuration_param(
        INTEGRATION_NAME,
        "Slack API Key",
    )
    param_slack_channel = siemplify.extract_configuration_param(
        INTEGRATION_NAME,
        "Slack Channel",
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    try:
        pX = PerimeterXManager(
            slack_channel=param_slack_channel,
            slack_api_key=param_slack_api_key,
            connector_type="slack",
        )
        pX.auth()
        output_message = "Connection to Slack established successfully."
        result = "true"
        status = EXECUTION_STATE_COMPLETED
        siemplify.LOGGER.info(
            f"Script Name: {SCRIPT_NAME} | {output_message}",
        )
    except PerimeterXManagerException as e:
        output_message = f"An error occurred when trying to connect to the API: {e}"
        result = "false"
        status = EXECUTION_STATE_FAILED
        siemplify.LOGGER.error(
            f"Script Name: {SCRIPT_NAME} | {output_message}",
        )
        siemplify.LOGGER.exception(e)

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"Result: {result}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")

    siemplify.end(output_message, result, status)


if __name__ == "__main__":
    main()
