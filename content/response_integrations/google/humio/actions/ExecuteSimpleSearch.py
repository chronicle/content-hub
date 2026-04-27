from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from TIPCommon import extract_configuration_param, extract_action_param, construct_csv
from ..core.HumioManager import HumioManager
from ..core.constants import (
    INTEGRATION_NAME,
    INTEGRATION_DISPLAY_NAME,
    EXECUTE_SIMPLE_SEARCH_SCRIPT_NAME,
)
from ..core.UtilsManager import get_timestamps, convert_comma_separated_to_list


TABLE_NAME = "Results"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = EXECUTE_SIMPLE_SEARCH_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Root",
        is_mandatory=True,
        print_value=True,
    )
    api_token = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Token",
        is_mandatory=True,
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        is_mandatory=True,
        input_type=bool,
        print_value=True,
    )

    # Action parameters
    repository_name = extract_action_param(
        siemplify, param_name="Repository Name", is_mandatory=True, print_value=True
    )
    query = extract_action_param(siemplify, param_name="Query Filter", print_value=True)
    timeframe = extract_action_param(
        siemplify, param_name="Time Frame", print_value=True
    )
    start_time_string = extract_action_param(
        siemplify, param_name="Start Time", print_value=True
    )
    end_time_string = extract_action_param(
        siemplify, param_name="End Time", print_value=True
    )
    fields_to_return_string = extract_action_param(
        siemplify, param_name="Fields To Return", print_value=True
    )
    sort_field = extract_action_param(
        siemplify, param_name="Sort Field", print_value=True
    )
    sort_field_type = extract_action_param(
        siemplify, param_name="Sort Field Type", print_value=True
    )
    sort_order = extract_action_param(
        siemplify, param_name="Sort Order", print_value=True
    )
    limit = extract_action_param(
        siemplify,
        param_name="Max Results To Return",
        input_type=int,
        default_value=50,
        print_value=True,
    )

    fields_to_return = convert_comma_separated_to_list(fields_to_return_string)

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    result = True
    status = EXECUTION_STATE_COMPLETED
    output_message = ""

    try:
        if limit is not None and limit < 1:
            raise Exception('"Max Results To Return" must be greater than 0.')

        start_time, end_time = get_timestamps(
            timeframe, start_time_string, end_time_string
        )

        if start_time > end_time:
            raise Exception("End Time should be later than Start Time")

        manager = HumioManager(
            api_root=api_root,
            api_token=api_token,
            verify_ssl=verify_ssl,
            siemplify_logger=siemplify.LOGGER,
        )

        results, constructed_query = manager.get_events_by_custom_query(
            repository_name,
            query,
            limit,
            start_time,
            end_time,
            fields_to_return,
            sort_field,
            sort_field_type,
            sort_order,
        )

        if results:
            siemplify.result.add_result_json([result.to_json() for result in results])
            siemplify.result.add_data_table(
                TABLE_NAME, construct_csv([result.to_table() for result in results])
            )
            output_message += (
                f'Successfully returned results for the query "{constructed_query}" in '
                f"{INTEGRATION_DISPLAY_NAME}."
            )
        else:
            output_message = f'No results were found for the query "{constructed_query}" in {INTEGRATION_DISPLAY_NAME}.'

    except Exception as e:
        siemplify.LOGGER.error(
            f"General error performing action {EXECUTE_SIMPLE_SEARCH_SCRIPT_NAME}"
        )
        siemplify.LOGGER.exception(e)
        result = False
        status = EXECUTION_STATE_FAILED
        output_message = (
            f'Error executing action "{EXECUTE_SIMPLE_SEARCH_SCRIPT_NAME}". Reason: {e}'
        )

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"Result: {result}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")

    siemplify.end(output_message, result, status)


if __name__ == "__main__":
    main()
