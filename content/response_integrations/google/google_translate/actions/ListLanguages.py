from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyAction import SiemplifyAction
from ..core.GoogleTranslateManager import GoogleTranslateManager
from TIPCommon import extract_configuration_param, extract_action_param
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from ..core.constants import (
    INTEGRATION_NAME,
    INTEGRATION_DISPLAY_NAME,
    LIST_LANGUAGES_SCRIPT_NAME,
    FILTER_KEY_MAPPING,
    FILTER_STRATEGY_MAPPING,
    DEFAULT_RECORDS_LIMIT,
)
from TIPCommon import construct_csv


TABLE_NAME = "Available Languages"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = LIST_LANGUAGES_SCRIPT_NAME
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

    # Action parameters
    filter_key = extract_action_param(
        siemplify, param_name="Filter Key", print_value=True
    )
    filter_logic = extract_action_param(
        siemplify, param_name="Filter Logic", print_value=True
    )
    filter_value = extract_action_param(
        siemplify, param_name="Filter Value", print_value=True
    )
    limit = extract_action_param(
        siemplify,
        param_name="Max Records To Return",
        input_type=int,
        default_value=DEFAULT_RECORDS_LIMIT,
        print_value=True,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    result = True
    status = EXECUTION_STATE_COMPLETED

    try:
        if not FILTER_KEY_MAPPING.get(filter_key) and FILTER_STRATEGY_MAPPING.get(
            filter_logic
        ):
            raise Exception(
                'you need to select a field from the "Filter Key" parameter'
            )

        if limit <= 0:
            raise Exception(
                f'Invalid value was provided for "Max Records to Return": {limit}. '
                f"Positive number should be provided"
            )

        manager = GoogleTranslateManager(
            api_root=api_root,
            api_key=api_key,
            verify_ssl=verify_ssl,
            siemplify_logger=siemplify.LOGGER,
        )

        languages = manager.get_languages(filter_key, filter_logic, filter_value, limit)

        if languages:
            siemplify.result.add_data_table(
                TABLE_NAME, construct_csv([language.to_csv() for language in languages])
            )
            siemplify.result.add_result_json(
                {"languages": [language.to_json() for language in languages]}
            )
            output_message = f"Successfully found languages for the provided criteria in {INTEGRATION_DISPLAY_NAME}."
        else:
            result = False
            output_message = f"No languages were found for the provided criteria in {INTEGRATION_DISPLAY_NAME}."

        if (
            FILTER_KEY_MAPPING.get(filter_key)
            and FILTER_STRATEGY_MAPPING.get(filter_logic)
            and not filter_value
        ):
            output_message += '\nThe filter was not applied, because parameter "Filter Value" has an empty value.'

    except Exception as e:
        siemplify.LOGGER.error(
            f"General error performing action {LIST_LANGUAGES_SCRIPT_NAME}"
        )
        siemplify.LOGGER.exception(e)
        result = False
        status = EXECUTION_STATE_FAILED
        output_message = (
            f'Error executing action "{LIST_LANGUAGES_SCRIPT_NAME}". Reason: {e}'
        )

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"Result: {result}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")

    siemplify.end(output_message, result, status)


if __name__ == "__main__":
    main()
