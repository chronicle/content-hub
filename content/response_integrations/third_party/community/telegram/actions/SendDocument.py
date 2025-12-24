from __future__ import annotations

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

from ..core.TelegramManager import TelegramManager

IDENTIFIER = "Telegram"
SCRIPT_NAME = "Send Document"


@output_handler
def main():
    siemplify = SiemplifyAction()

    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    bot_api_token = siemplify.extract_configuration_param(IDENTIFIER, "API Token")

    chat_id = siemplify.extract_action_param("Chat ID")
    doc_url = siemplify.extract_action_param("Document URL")

    sent_doc = {}

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    try:
        telegram_manager = TelegramManager(bot_api_token)
        sent_doc = telegram_manager.send_doc(chat_id, doc_url)
    except Exception as e:
        output_message = f"Failed to send document. Error: {e}"
        return_value = False
        status = EXECUTION_STATE_FAILED
    else:
        output_message = "The document was sent successfully"
        return_value = True
        status = EXECUTION_STATE_COMPLETED

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")

    siemplify.result.add_result_json(sent_doc)
    siemplify.end(output_message, return_value, status)


if __name__ == "__main__":
    main()
