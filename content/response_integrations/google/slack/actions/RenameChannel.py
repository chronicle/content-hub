from __future__ import annotations
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from ..core.SlackManager import SlackManager, SlackManagerException
from TIPCommon import extract_configuration_param, extract_action_param
from ..core.consts import PROVIDER_NAME

SCRIPT_NAME = f"{PROVIDER_NAME} - RenameChannel"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    api_token = extract_configuration_param(
        siemplify, provider_name=PROVIDER_NAME, param_name="ApiToken", input_type=str
    )

    channel_name = extract_action_param(
        siemplify,
        param_name="Channel Name",
        is_mandatory=False,
        print_value=True,
        input_type=str,
    )

    channel_id = extract_action_param(
        siemplify,
        param_name="Channel ID",
        is_mandatory=False,
        print_value=True,
        input_type=str,
    )

    new_name = extract_action_param(
        siemplify,
        param_name="New Name",
        is_mandatory=True,
        print_value=True,
        input_type=str,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    result = "false"
    status = EXECUTION_STATE_COMPLETED

    if not channel_name and not channel_id:
        status = EXECUTION_STATE_FAILED
        result = "false"
        output_message = "You have to specify either the Channel Name or the Channel ID"

    else:
        try:
            slack_manager = SlackManager(api_token)

            if channel_id:
                json_result = slack_manager.rename_channel_by_id(channel_id, new_name)
                output_message = (
                    f"Successfully renamed channel with ID: {channel_id} to {new_name}."
                )
            else:
                channel = slack_manager.get_channel_by_name(channel_name)
                json_result = slack_manager.rename_channel_by_id(channel.id, new_name)

                output_message = (
                    f"Successfully renamed channel {channel_name} to {new_name}."
                )

            siemplify.result.add_result_json(json_result.raw_data)
            result = "true"

        except (SlackManagerException, Exception) as e:
            output_message = f"Error executing action RenameChannel. Reason: {e}"
            status = EXECUTION_STATE_FAILED
            siemplify.LOGGER.error(f"Error executing action {SCRIPT_NAME}")
            siemplify.LOGGER.exception(e)

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"Result: {result}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.end(output_message, result, status)


if __name__ == "__main__":
    main()
