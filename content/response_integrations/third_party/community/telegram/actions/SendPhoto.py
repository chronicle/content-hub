from __future__ import annotations

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

from ..core.TelegramManager import TelegramManager

IDENTIFIER = "Telegram"
SCRIPT_NAME = "Send Photo"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = SCRIPT_NAME

    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")
    bot_api_token = siemplify.extract_configuration_param(IDENTIFIER, "API Token")

    chat_id = siemplify.extract_action_param("Chat ID")
    photo_url = siemplify.extract_action_param("Photo URL")
    sent_photo = {}

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    try:
        telegram_manager = TelegramManager(bot_api_token)
        sent_photo = telegram_manager.send_photo(chat_id, photo_url)
    except Exception as e:
        return_value = False
        output_message = f"Could not send photo. Error: {e!s}"
        status = EXECUTION_STATE_FAILED
    else:
        output_message = "The photo was sent successfully"
        return_value = True
        status = EXECUTION_STATE_COMPLETED

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.result.add_result_json(sent_photo)
    siemplify.end(output_message, return_value, status)


if __name__ == "__main__":
    main()
