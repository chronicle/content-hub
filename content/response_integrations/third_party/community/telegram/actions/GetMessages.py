from __future__ import annotations

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

from ..core.TelegramManager import TelegramManager

IDENTIFIER = "Telegram"
SCRIPT_NAME = "Get Messages"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = SCRIPT_NAME

    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    bot_api_token = siemplify.extract_configuration_param(IDENTIFIER, "API Token")
    offset_param = siemplify.extract_action_param("Offset Param")
    allowed_updates = siemplify.extract_action_param("Allowed Updates")

    all_messages = {}

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    try:
        telegram_manager = TelegramManager(bot_api_token)

        all_messages = telegram_manager.get_messages(offset_param, allowed_updates)

    except Exception as e:
        output_message = f"Could not get messages. Error: {e}"
        return_value = False
        status = EXECUTION_STATE_FAILED
    else:
        return_value = True
        output_message = "The messages were pulled successfully."
        status = EXECUTION_STATE_COMPLETED

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.result.add_result_json(all_messages)
    siemplify.end(output_message, return_value, status)


if __name__ == "__main__":
    main()
