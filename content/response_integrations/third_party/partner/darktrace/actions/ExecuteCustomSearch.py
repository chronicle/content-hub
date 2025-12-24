from __future__ import annotations

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import convert_unixtime_to_datetime, output_handler
from TIPCommon import extract_action_param, extract_configuration_param

from ..core.constants import (
    DEFAULT_RESULTS_LIMIT,
    EXECUTE_CUSTOM_SEARCH_SCRIPT_NAME,
    INTEGRATION_DISPLAY_NAME,
    INTEGRATION_NAME,
)
from ..core.DarktraceExceptions import InvalidTimeException
from ..core.DarktraceManager import DarktraceManager
from ..core.UtilsManager import get_datetimes


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = EXECUTE_CUSTOM_SEARCH_SCRIPT_NAME
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
        print_value=True,
    )
    api_private_token = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Private Token",
        is_mandatory=True,
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        input_type=bool,
        print_value=True,
    )

    # Action parameters
    query = extract_action_param(siemplify, param_name="Query", is_mandatory=True, print_value=True)
    timeframe = extract_action_param(siemplify, param_name="Time Frame", print_value=True)
    start_time_string = extract_action_param(siemplify, param_name="Start Time", print_value=True)
    end_time_string = extract_action_param(siemplify, param_name="End Time", print_value=True)
    limit = extract_action_param(
        siemplify,
        param_name="Max Results To Return",
        input_type=int,
        default_value=DEFAULT_RESULTS_LIMIT,
        print_value=True,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    result = True
    status = EXECUTION_STATE_COMPLETED

    try:
        if limit < 1:
            siemplify.LOGGER.info(
                f'"Max Results To Return" must be greater than zero. The default value '
                f"{DEFAULT_RESULTS_LIMIT} will be used"
            )
            limit = DEFAULT_RESULTS_LIMIT

        alert_start_time = convert_unixtime_to_datetime(
            int(siemplify._current_alert.additional_properties.get("StartTime"))
        )
        alert_end_time = convert_unixtime_to_datetime(
            int(siemplify._current_alert.additional_properties.get("EndTime"))
        )

        start_time, end_time = get_datetimes(
            range_string=timeframe,
            start_time_string=start_time_string,
            end_time_string=end_time_string,
            alert_start_time=alert_start_time,
            alert_end_time=alert_end_time,
        )

        manager = DarktraceManager(
            api_root=api_root,
            api_token=api_token,
            api_private_token=api_private_token,
            verify_ssl=verify_ssl,
            siemplify_logger=siemplify.LOGGER,
        )

        results = manager.execute_custom_query(query, start_time, end_time, limit)
        siemplify.result.add_result_json({"hits": [result.to_json() for result in results]})

        if results:
            output_message = (
                f'Successfully returned results for the query "{query}" in'
                f" {INTEGRATION_DISPLAY_NAME}."
            )
        else:
            output_message = (
                f'No results were found for the query "{query}" in {INTEGRATION_DISPLAY_NAME}.'
            )
    except InvalidTimeException:
        result = False
        status = EXECUTION_STATE_FAILED
        output_message = (
            f'Error executing action "{EXECUTE_CUSTOM_SEARCH_SCRIPT_NAME}". Reason: "Start Time" '
            f'should be provided, when "Custom" is selected in "Time Frame" parameter.'
        )
    except Exception as e:
        siemplify.LOGGER.error(
            f"General error performing action {EXECUTE_CUSTOM_SEARCH_SCRIPT_NAME}"
        )
        siemplify.LOGGER.exception(e)
        result = False
        status = EXECUTION_STATE_FAILED
        output_message = f"Error executing action {EXECUTE_CUSTOM_SEARCH_SCRIPT_NAME}. Reason: {e}"

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"Result: {result}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")

    siemplify.end(output_message, result, status)


if __name__ == "__main__":
    main()
