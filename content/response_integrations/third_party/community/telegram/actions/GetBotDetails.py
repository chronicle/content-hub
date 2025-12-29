from __future__ import annotations

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

from ..core.TelegramManager import TelegramManager

IDENTIFIER = "Telegram"
SCRIPT_NAME = "Get Bot Details"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = SCRIPT_NAME

    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")
    bot_api_token = siemplify.extract_configuration_param(IDENTIFIER, "API Token")

    bot_details = {}

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    try:
        telegram_manager = TelegramManager(bot_api_token)
        bot_details = telegram_manager.get_bot_details()

    except Exception as e:
        output_message = f"The Bot details could not be fetched. Error: {e}"
        return_value = False
        status = EXECUTION_STATE_FAILED
    else:
        return_value = True
        output_message = "The Bot was found successfully"
        status = EXECUTION_STATE_COMPLETED

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")

    siemplify.result.add_result_json(bot_details)
    siemplify.end(output_message, return_value, status)


if __name__ == "__main__":
    main()
