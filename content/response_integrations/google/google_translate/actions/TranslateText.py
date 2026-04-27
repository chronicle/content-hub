from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyAction import SiemplifyAction
from ..core.GoogleTranslateManager import GoogleTranslateManager
from ..core.constants import (
    INTEGRATION_NAME,
    INTEGRATION_DISPLAY_NAME,
    TRANSLATE_TEXT_SCRIPT_NAME,
)
from TIPCommon import extract_configuration_param, extract_action_param
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = TRANSLATE_TEXT_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Root",
        is_mandatory=True,
        print_value=True,
    )
    api_key = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Key",
        is_mandatory=True,
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        input_type=bool,
        is_mandatory=True,
        print_value=True,
    )

    source_language = extract_action_param(
        siemplify, param_name="Source Language", print_value=True
    )
    target_language = extract_action_param(
        siemplify, param_name="Target Language", is_mandatory=True, print_value=True
    )
    text = extract_action_param(
        siemplify, param_name="Text", is_mandatory=True, print_value=True
    )

    status = EXECUTION_STATE_COMPLETED
    result_value = True
    output_message = ""

    try:
        siemplify.LOGGER.info("----------------- Main - Started -----------------")
        manager = GoogleTranslateManager(
            api_root=api_root,
            api_key=api_key,
            verify_ssl=verify_ssl,
            siemplify_logger=siemplify.LOGGER,
        )

        translation_json = manager.translate_text(
            source_language=source_language, target_language=target_language, text=text
        )
        siemplify.result.add_result_json(translation_json)
        output_message = (
            f"Successfully translated the provided text in {INTEGRATION_DISPLAY_NAME}."
        )

    except Exception as e:
        output_message += (
            f"Error executing action {TRANSLATE_TEXT_SCRIPT_NAME}. Reason: {e}"
        )
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        result_value = False

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  result_value: {result_value}\n  output_message: {output_message}"
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
