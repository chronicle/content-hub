from __future__ import annotations

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

from ..core.TelegramManager import TelegramManager

IDENTIFIER = "Telegram"
SCRIPT_NAME = "Send Pool"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = SCRIPT_NAME

    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    bot_api_token = siemplify.extract_configuration_param(IDENTIFIER, "API Token")

    chat_id = siemplify.extract_action_param("Chat ID")
    question_to_ask = siemplify.extract_action_param("Question")
    answer_options = siemplify.extract_action_param("Options")
    is_anonymous = siemplify.extract_action_param("Is Anonymous")

    sent_poll = {}

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    try:
        telegram_manager = TelegramManager(bot_api_token)
        sent_poll = telegram_manager.ask_question(
            chat_id,
            question_to_ask,
            answer_options,
            is_anonymous,
        )

    except Exception as e:
        output_message = f"Could not send poll. Error: {e}"
        return_value = False
        status = EXECUTION_STATE_FAILED
    else:
        return_value = True
        output_message = f'The poll "{question_to_ask}" was sent successfully.'
        status = EXECUTION_STATE_COMPLETED

    siemplify.result.add_result_json(sent_poll)
    siemplify.end(output_message, return_value, status)


if __name__ == "__main__":
    main()
