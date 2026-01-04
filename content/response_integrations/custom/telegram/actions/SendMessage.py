from __future__ import annotations

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

from ..core.TelegramManager import TelegramManager

IDENTIFIER = "Telegram"
SCRIPT_NAME = "Send Message"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = SCRIPT_NAME

    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    json_result = {}

    bot_api_token = siemplify.extract_configuration_param(IDENTIFIER, "API Token")
    message_content = siemplify.extract_action_param("Message")
    chat_id = siemplify.extract_action_param("Chat ID")

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    try:
        telegram_manager = TelegramManager(bot_api_token)

        sent_message = telegram_manager.telegram_bot_sendmessage(
            chat_id,
            message_content,
        )

        json_result = sent_message

    except Exception as e:
        output_message = f"Could not send message. Error: {e}"
        return_value = False
        status = EXECUTION_STATE_FAILED
    else:
        output_message = "The message was sent successfully"
        return_value = True
        status = EXECUTION_STATE_COMPLETED

    siemplify.result.add_result_json(json_result)
    siemplify.end(output_message, return_value, status)


if __name__ == "__main__":
    main()
