from __future__ import annotations

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

from ..core.TelegramManager import TelegramManager

IDENTIFIER = "Telegram"
SCRIPT_NAME = "Set Default Chat Permissions"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = SCRIPT_NAME

    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    bot_api_token = siemplify.extract_configuration_param(IDENTIFIER, "API Token")

    chat_id = siemplify.extract_action_param("Chat ID")
    can_send_polls = siemplify.extract_action_param("Can Send Polls")
    can_pin_messages = siemplify.extract_action_param("Can Pin Messages")
    can_invite_user = siemplify.extract_action_param("Can Invite Users")
    can_edit_the_info = siemplify.extract_action_param("Can Edit Info")
    can_post_messages = siemplify.extract_action_param("Can Send Messages")

    default_chat_permissions = {}

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    try:
        telegram_manager = TelegramManager(bot_api_token)

        default_chat_permissions = telegram_manager.set_default_chat_permissions(
            chat_id,
            can_send_polls,
            can_pin_messages,
            can_invite_user,
            can_edit_the_info,
            can_post_messages,
        )

    except Exception as e:
        output_message = f"Could not change the chat permissions. Error: {e}"
        return_value = False
        status = EXECUTION_STATE_FAILED
    else:
        output_message = (
            f"The permissions of the chat {chat_id} were changed successfully"
        )
        return_value = True
        status = EXECUTION_STATE_COMPLETED

    siemplify.result.add_result_json(default_chat_permissions)
    siemplify.end(output_message, return_value, status)


if __name__ == "__main__":
    main()
