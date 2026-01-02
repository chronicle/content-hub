from __future__ import annotations

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

from ..core.TelegramManager import TelegramManager

IDENTIFIER = "Telegram"
SCRIPT_NAME = "Ping"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = SCRIPT_NAME

    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")
    bot_api_token = siemplify.extract_configuration_param(IDENTIFIER, "API Token")

    telegram_manager = TelegramManager(bot_api_token)

    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    try:
        response = telegram_manager.test_connectivity()
    except Exception:
        response = None

    if response:
        return_value = True
        output_message = "Connected successfully"
        status = EXECUTION_STATE_COMPLETED

    else:
        return_value = False
        output_message = "The Connection failed"
        status = EXECUTION_STATE_FAILED

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.end(output_message, return_value, status)


if __name__ == "__main__":
    main()
