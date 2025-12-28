from __future__ import annotations

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

from ..core.TelegramManager import TelegramManager

IDENTIFIER = "Telegram"
SCRIPT_NAME = "Set User Permissions"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = SCRIPT_NAME

    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    bot_api_token = siemplify.extract_configuration_param(IDENTIFIER, "API Token")

    chat_id = siemplify.extract_action_param("Chat ID")
    user_id = siemplify.extract_action_param("User ID")
    is_anonymous = siemplify.extract_action_param("Is Anonymous")
    can_edit_the_info = siemplify.extract_action_param("Can Edit The Info")
    can_post_messages = siemplify.extract_action_param("Can Post Messages")
    can_edit_messages = siemplify.extract_action_param("Can Edit Messages")
    can_delete_messages = siemplify.extract_action_param("Can Delete Messages")
    can_invite_user = siemplify.extract_action_param("Can Invite Users")
    can_restrict_users = siemplify.extract_action_param("Can Restrict Members")
    can_promote_members = siemplify.extract_action_param("Can Promote Members")
    can_pin_messages = siemplify.extract_action_param("Can Pin Messages")

    user_permissions = {}

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    try:
        telegram_manager = TelegramManager(bot_api_token)

        user_permissions = telegram_manager.set_user_permissions(
            chat_id,
            user_id,
            is_anonymous,
            can_edit_the_info,
            can_post_messages,
            can_edit_messages,
            can_delete_messages,
            can_invite_user,
            can_restrict_users,
            can_pin_messages,
            can_promote_members,
        )

    except Exception as e:
        output_message = f"Could not set user permissions. Error: {e}"
        return_value = False
        status = EXECUTION_STATE_FAILED
    else:
        output_message = f"The permissions of the user {user_id} were set successfully"
        return_value = True
        status = EXECUTION_STATE_COMPLETED

    siemplify.result.add_result_json(user_permissions)
    siemplify.end(output_message, return_value, status)


if __name__ == "__main__":
    main()
