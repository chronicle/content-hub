from __future__ import annotations

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

from ..core.TelegramManager import TelegramManager

IDENTIFIER = "Telegram"
SCRIPT_NAME = "Get Chat Details"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = SCRIPT_NAME

    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")
    bot_api_token = siemplify.extract_configuration_param(IDENTIFIER, "API Token")
    chat_id = siemplify.extract_action_param("Chat ID")

    chat_details = {}
    title = ""
    link = ""

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    try:
        telegram_manager = TelegramManager(bot_api_token)

        chat_details = telegram_manager.get_chat_details(chat_id)

        title = "The chat invite link:"
        link = chat_details["result"]["invite_link"]

    except Exception as e:
        output_message = f"Could not find The chat {chat_id}. Error: {e}"
        return_value = False
        status = EXECUTION_STATE_FAILED
    else:
        return_value = True
        output_message = f"The chat {chat_id} was found successfully"
        status = EXECUTION_STATE_COMPLETED

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.result.add_link(title, link)
    siemplify.result.add_result_json(chat_details)
    siemplify.end(output_message, return_value, status)


if __name__ == "__main__":
    main()
