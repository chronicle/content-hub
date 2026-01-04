from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from TIPCommon import extract_configuration_param, extract_action_param, construct_csv
from ..core.SpyCloudManager import SpyCloudManager
from ..core.constants import (
    INTEGRATION_NAME,
    INTEGRATION_DISPLAY_NAME,
    LIST_CATALOGS_SCRIPT_NAME,
    EQUAL_FILTER,
    DEFAULT_CATALOGS_LIMIT,
)
from ..core.UtilsManager import get_timestamps

TABLE_NAME = "Available Catalogs"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = LIST_CATALOGS_SCRIPT_NAME
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
    filter_logic = extract_action_param(siemplify, param_name="Filter Logic", print_value=True)
    filter_value = extract_action_param(siemplify, param_name="Filter Value", print_value=True)
    timeframe = extract_action_param(
        siemplify, param_name="Time Frame", is_mandatory=True, print_value=True
    )
    start_time_string = extract_action_param(siemplify, param_name="Start Time", print_value=True)
    end_time_string = extract_action_param(siemplify, param_name="End Time", print_value=True)
    limit = extract_action_param(
        siemplify,
        param_name="Max Catalogs To Return",
        input_type=int,
        print_value=True,
        default_value=DEFAULT_CATALOGS_LIMIT,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    result = True
    status = EXECUTION_STATE_COMPLETED

    try:
        if limit < 0:
            raise Exception('"Max Catalogs To Return" should be a positive number.')

        start_time, end_time = get_timestamps(timeframe, start_time_string, end_time_string)

        manager = SpyCloudManager(
            api_root=api_root,
            api_key=api_key,
            verify_ssl=verify_ssl,
            siemplify_logger=siemplify.LOGGER,
        )

        catalogs = manager.get_catalogs(
            filter_value=filter_value, start_time=start_time, end_time=end_time
        )

        if filter_value is not None and filter_logic == EQUAL_FILTER:
            catalogs = [catalog for catalog in catalogs if catalog.title == filter_value]

        catalogs = catalogs[:limit]

        if catalogs:
            siemplify.result.add_result_json([catalog.to_json() for catalog in catalogs])
            siemplify.result.add_data_table(
                TABLE_NAME, construct_csv([catalog.to_table() for catalog in catalogs])
            )
            output_message = f"Successfully found catalogs for the provided criteria in {INTEGRATION_DISPLAY_NAME}"
        else:
            output_message = (
                f"No catalogs were found for the provided criteria in {INTEGRATION_DISPLAY_NAME}"
            )

    except Exception as e:
        siemplify.LOGGER.error(f"General error performing action {LIST_CATALOGS_SCRIPT_NAME}")
        siemplify.LOGGER.exception(e)
        result = False
        status = EXECUTION_STATE_FAILED
        output_message = f'Error executing action "{LIST_CATALOGS_SCRIPT_NAME}." Reason: {e}'

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"Result: {result}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")

    siemplify.end(output_message, result, status)


if __name__ == "__main__":
    main()
