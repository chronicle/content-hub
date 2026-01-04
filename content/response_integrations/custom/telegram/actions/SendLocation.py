from __future__ import annotations

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

from ..core.TelegramManager import TelegramManager

IDENTIFIER = "Telegram"
SCRIPT_NAME = "Send Location"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = SCRIPT_NAME

    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    bot_api_token = siemplify.extract_configuration_param(IDENTIFIER, "API Token")
    chat_id = siemplify.extract_action_param("Chat ID")
    location_latitude = siemplify.extract_action_param("Latitude")
    location_longitude = siemplify.extract_action_param("Longitude")

    sent_location = {}

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    try:
        telegram_manager = TelegramManager(bot_api_token)

        sent_location = telegram_manager.send_location(
            chat_id,
            location_latitude,
            location_longitude,
        )
    except Exception as e:
        output_message = f"Could not sent location. Error: {e}"
        return_value = False
        status = EXECUTION_STATE_FAILED
    else:
        output_message = "The location was sent successfully"
        return_value = True
        status = EXECUTION_STATE_COMPLETED

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")

    siemplify.result.add_result_json(sent_location)
    siemplify.end(output_message, return_value, status)


if __name__ == "__main__":
    main()
