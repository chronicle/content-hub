from __future__ import annotations
import re

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler, convert_dict_to_json_result_dict
from ..core.SlackManager import SlackManager, SlackManagerException, UserNotFoundException
from TIPCommon import extract_configuration_param, extract_action_param
from ..core.consts import PROVIDER_NAME

SCRIPT_NAME = f"{PROVIDER_NAME} - SendMessage"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    api_token = extract_configuration_param(
        siemplify, provider_name=PROVIDER_NAME, param_name="ApiToken", input_type=str
    )

    message = extract_action_param(
        siemplify,
        param_name="Message",
        is_mandatory=True,
        print_value=True,
        input_type=str,
    )

    channels = extract_action_param(
        siemplify,
        param_name="Channel",
        is_mandatory=True,
        print_value=True,
        input_type=str,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    json_result = {}

    try:
        channels = [channel.strip() for channel in channels.split(",")]
        slack_manager = SlackManager(api_token)

        for channel in channels:
            if re.search(r"^[A-Za-z0-9\.\+_-]+@[A-Za-z0-9\._-]+\.[a-zA-Z]*$", channel):
                siemplify.LOGGER.info(
                    f"{channel} seems to be an email. Searching for matching user"
                )

                try:
                    user = slack_manager.get_user_details_by_email(channel)
                    sent_message = slack_manager.send_message(user.id, message)
                    json_result[channel] = slack_manager.get_json_channel_message(
                        sent_message.raw_data
                    )
                    continue

                except UserNotFoundException:
                    siemplify.LOGGER.info(
                        f"User with email {channel} was not found, will try to use {channel} "
                        f"as channel ID."
                    )

            sent_message = slack_manager.send_message(channel, message)
            json_result[channel] = slack_manager.get_json_channel_message(
                sent_message.raw_data
            )

        msg_channels = ", ".join(channels)
        output_message = (
            f'Message "{message}" was sent to the following channels: {msg_channels}.'
        )
        result = "true"
        status = EXECUTION_STATE_COMPLETED
        siemplify.LOGGER.info(f"Script Name: {SCRIPT_NAME} | {output_message}")

    except (SlackManagerException, Exception) as e:
        output_message = f"An error occurred when trying to send message: {e}"
        result = "false"
        status = EXECUTION_STATE_FAILED
        siemplify.LOGGER.error(f"Script Name: {SCRIPT_NAME} | {output_message}")
        siemplify.LOGGER.exception(e)

    siemplify.result.add_result_json(convert_dict_to_json_result_dict(json_result))
    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"Result: {result}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")

    siemplify.end(output_message, result, status)


if __name__ == "__main__":
    main()
