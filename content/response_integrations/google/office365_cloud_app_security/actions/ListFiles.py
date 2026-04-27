from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from ..core.Office365CloudAppSecurityManager import Office365CloudAppSecurityManager
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from TIPCommon import extract_configuration_param, extract_action_param, construct_csv
from ..core.constants import (
    INTEGRATION_NAME,
    LIST_FILES_SCRIPT_NAME,
    FILTER_KEY_MAPPING,
    FILTER_STRATEGY_MAPPING,
    DEFAULT_LIMIT,
    FILE_TYPE_MAPPING,
    SHARE_STATUS_MAPPING,
    PRODUCT,
    CONTAINS,
    FILETYPE_FILTER_KEY,
    SHARE_STATUS_FILTER_KEY,
    POSSIBLE_FILE_TYPES,
    POSSIBLE_SHARE_STATUSES,
    MAX_LIMIT,
)


TABLE_NAME = "Available Files"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = LIST_FILES_SCRIPT_NAME
    siemplify.LOGGER.info("================= Main - Param Init =================")

    # INIT INTEGRATION CONFIGURATION:
    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="portal URL",
        input_type=str,
    )

    api_token = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API token",
        input_type=str,
    )

    filter_key = extract_action_param(
        siemplify, param_name="Filter Key", print_value=True
    )
    filter_logic = extract_action_param(
        siemplify, param_name="Filter Logic", print_value=True
    )
    filter_value = extract_action_param(
        siemplify, param_name="Filter Value", print_value=True
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    status = EXECUTION_STATE_COMPLETED
    output_message = f"Successfully found files for the provided criteria in {PRODUCT}."
    result_value = True

    try:
        limit = extract_action_param(
            siemplify,
            param_name="Max Records To Return",
            input_type=int,
            default_value=DEFAULT_LIMIT,
            print_value=True,
        )

        if limit <= 0:
            raise Exception(
                f'Invalid value provided for "Max Records to Return": {limit}. '
                f"Positive number should be provided"
            )

        if not FILTER_KEY_MAPPING.get(filter_key) and FILTER_STRATEGY_MAPPING.get(
            filter_logic
        ):
            raise Exception(
                'you need to select a field from the "Filter Key" parameter'
            )

        if filter_logic == CONTAINS:
            if filter_key in [FILETYPE_FILTER_KEY, SHARE_STATUS_FILTER_KEY]:
                raise Exception(
                    f'only "ID" and "Filename" are supported for "Contains" filter logic.'
                )
        else:
            if filter_value:
                if filter_key == FILETYPE_FILTER_KEY:
                    if filter_value.lower() not in POSSIBLE_FILE_TYPES:
                        raise Exception(
                            f'invalid value provided for "File Type" filter. Possible values: Other, '
                            f"Document, Spreadsheet, Presentation, Text, Image, Folder."
                        )
                    filter_value = FILE_TYPE_MAPPING.get(filter_value.lower())
                elif filter_key == SHARE_STATUS_FILTER_KEY:
                    if filter_value.lower() not in POSSIBLE_SHARE_STATUSES:
                        raise Exception(
                            f'invalid value provided for "Share Status" filter. Possible values: '
                            f"Public (Internet), Public, External, Internal, Private."
                        )
                    filter_value = SHARE_STATUS_MAPPING.get(filter_value.lower())

        manager = Office365CloudAppSecurityManager(
            api_root=api_root, api_token=api_token, siemplify=siemplify
        )
        files = manager.list_files(
            filter_key=FILTER_KEY_MAPPING.get(filter_key),
            filter_logic=filter_logic,
            filter_value=filter_value,
            limit=limit if filter_logic != CONTAINS else MAX_LIMIT,
        )

        if files:
            json_results = [file.to_json() for file in files]
            csv_result = [file.to_csv() for file in files]
            siemplify.result.add_data_table(
                title=TABLE_NAME, data_table=construct_csv(csv_result)
            )
            siemplify.result.add_result_json(json_results)

            if (
                FILTER_KEY_MAPPING.get(filter_key)
                and FILTER_STRATEGY_MAPPING.get(filter_logic)
                and filter_value is None
            ):
                output_message += '\nThe filter was not applied, because parameter "Filter Value" has an empty value.'
        else:
            result_value = False
            output_message = (
                f"No files were found for the provided criteria in {PRODUCT}"
            )

    except Exception as e:
        output_message = (
            f'Error executing action "{LIST_FILES_SCRIPT_NAME}". Reason: {e}'
        )
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        result_value = False

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}:")
    siemplify.LOGGER.info(f"Result Value: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
