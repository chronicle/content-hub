from __future__ import annotations
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from ..core.SlackManager import SlackManager, SlackManagerException
from TIPCommon import extract_configuration_param, extract_action_param
from ..core.consts import PROVIDER_NAME

SCRIPT_NAME = f"{PROVIDER_NAME} - UploadFile"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    api_token = extract_configuration_param(
        siemplify, provider_name=PROVIDER_NAME, param_name="ApiToken", input_type=str
    )

    file_name = extract_action_param(
        siemplify,
        param_name="File Name",
        is_mandatory=True,
        print_value=True,
        input_type=str,
    )

    file_path = extract_action_param(
        siemplify,
        param_name="File Path",
        is_mandatory=True,
        print_value=True,
        input_type=str,
    )

    channel = extract_action_param(
        siemplify,
        param_name="Channel",
        is_mandatory=True,
        print_value=True,
        input_type=str,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    try:
        slack_manager = SlackManager(api_token)
        file_url = slack_manager.upload_file(file_name, file_path, channel)
        siemplify.result.add_link(f"Slack uploaded file URL {file_name}: ", file_url)
        output_message = (
            f"File {file_name} was successfully uploaded to {channel} channel."
        )
        result = "true"
        status = EXECUTION_STATE_COMPLETED
        siemplify.LOGGER.info(f"Script Name: {SCRIPT_NAME} | {output_message}")
    except (SlackManagerException, Exception) as e:
        output_message = f"An error occurred when trying to upload file: {e}"
        result = "false"
        status = EXECUTION_STATE_FAILED
        siemplify.LOGGER.error(f"Script Name: {SCRIPT_NAME} | {output_message}")
        siemplify.LOGGER.exception(e)

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"Result: {result}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")

    siemplify.end(output_message, result, status)


if __name__ == "__main__":
    main()
