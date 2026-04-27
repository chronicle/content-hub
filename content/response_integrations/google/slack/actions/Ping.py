from __future__ import annotations
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from ..core.SlackManager import SlackManager, SlackManagerException, UserAuthException
from TIPCommon import extract_configuration_param
from ..core.consts import PROVIDER_NAME

SCRIPT_NAME = f"{PROVIDER_NAME} - Ping"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    api_token = extract_configuration_param(
        siemplify, provider_name=PROVIDER_NAME, param_name="ApiToken", input_type=str
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    result = "false"
    status = EXECUTION_STATE_FAILED

    try:
        slack_manager = SlackManager(api_token)
        slack_manager.test_connectivity()
        output_message = "Connection to Slack established successfully."
        result = "true"
        status = EXECUTION_STATE_COMPLETED
        siemplify.LOGGER.info(f"Script Name: {SCRIPT_NAME} | {output_message}")

    except (SlackManagerException, UserAuthException) as e:
        output_message = f'Failed to execute "Ping": {e}'
        siemplify.LOGGER.error(f"Script Name: {SCRIPT_NAME} | {output_message}")
        siemplify.LOGGER.exception(e)

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"Result: {result}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")

    siemplify.end(output_message, result, status)


if __name__ == "__main__":
    main()
