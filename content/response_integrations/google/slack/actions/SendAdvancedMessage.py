from __future__ import annotations
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler, convert_dict_to_json_result_dict
from ..core.SlackManager import (
    SlackManager,
    SlackManagerException,
    UserNotFoundException,
    ChannelNotFoundException,
)
from TIPCommon import extract_configuration_param, extract_action_param
from ..core.consts import PROVIDER_NAME

SCRIPT_NAME = f"{PROVIDER_NAME} - SendAdvancedMessage"


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

    message_type = extract_action_param(
        siemplify,
        param_name="Message Type",
        is_mandatory=True,
        print_value=True,
        input_type=str,
    )

    recipient = extract_action_param(
        siemplify,
        param_name="Recipient",
        is_mandatory=True,
        print_value=True,
        input_type=str,
    )

    recipient_type = extract_action_param(
        siemplify,
        param_name="Recipient Type",
        default_value="Name",
        is_mandatory=True,
        print_value=True,
        input_type=str,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    json_result = {}
    result = "false"

    try:
        slack_manager = SlackManager(api_token)

        try:
            # Try to extract the ID of User by name or email
            if recipient_type == "Name":
                all_users = slack_manager.list_users()
                user = slack_manager.get_user_by_name(all_users, username=recipient)
                if user:
                    recipient = user.id
            elif recipient_type == "Email":
                user = slack_manager.get_user_details_by_email(recipient)
                recipient = user.id
        except UserNotFoundException as _:
            pass

        try:
            # Try to send a message by user ID, channel ID or channel name
            sent_message = slack_manager.send_message(
                recipient, message, message_type.lower()
            )
            json_result[recipient] = slack_manager.get_json_channel_message(
                sent_message.raw_data
            )
            output_message = "Message was sent successfully"
            result = "true"
            siemplify.LOGGER.info(f"Script Name: {SCRIPT_NAME} | {output_message}")
        except (UserNotFoundException, ChannelNotFoundException) as _:
            output_message = (
                f"Message was not sent as the specified recipient {recipient} "
                f"with type {recipient_type} was not found"
            )
        except Exception as e:
            output_message = f"Message was not sent because of occurred error: {e}"

        status = EXECUTION_STATE_COMPLETED

    except (SlackManagerException, Exception) as e:
        output_message = f"Send Advanced Message action! Error is: {e}"
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
