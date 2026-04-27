from __future__ import annotations
from ..core.AWSCloudWatchManager import AWSCloudWatchManager
from TIPCommon import extract_configuration_param, extract_action_param, construct_csv
from ..core.consts import (
    INTEGRATION_DISPLAY_NAME,
    SEARCH_LOG_EVENTS,
    TIME_FRAME_MAPPING,
    DEFAULT_MIN_RESULTS,
)
from ..core.utils import load_csv_to_list, get_time_frame
from ..core.exceptions import AWSCloudWatchInvalidParameterException

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler, unix_now


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = f"{INTEGRATION_DISPLAY_NAME} - {SEARCH_LOG_EVENTS}"
    siemplify.LOGGER.info("================= Main - Param Init =================")

    # INIT INTEGRATION CONFIGURATION:
    aws_access_key = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_DISPLAY_NAME,
        param_name="AWS Access Key ID",
        is_mandatory=True,
    )

    aws_secret_key = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_DISPLAY_NAME,
        param_name="AWS Secret Key",
        is_mandatory=True,
    )

    aws_default_region = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_DISPLAY_NAME,
        param_name="AWS Default Region",
        is_mandatory=True,
    )

    log_group_name = extract_action_param(
        siemplify, param_name="Log Group", is_mandatory=True, print_value=True
    )

    log_streams_names = extract_action_param(
        siemplify, param_name="Log Streams", is_mandatory=False, print_value=True
    )

    time_frame = extract_action_param(
        siemplify,
        param_name="Time Frame",
        is_mandatory=False,
        print_value=True,
        default_value="Last Hour",
    )

    start_time = extract_action_param(
        siemplify, param_name="Start Time", is_mandatory=False, print_value=True
    )

    end_time = extract_action_param(
        siemplify, param_name="End Time", is_mandatory=False, print_value=True
    )

    custom_filter = extract_action_param(
        siemplify, param_name="Custom Filter", is_mandatory=False, print_value=True
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    result_value = False
    try:
        max_events_to_return = extract_action_param(
            siemplify,
            param_name="Max Events To Return",
            input_type=int,
            is_mandatory=False,
            print_value=True,
            default_value=50,
        )

        if max_events_to_return < DEFAULT_MIN_RESULTS:
            raise AWSCloudWatchInvalidParameterException(
                f"'Max Events To Return' should be greater than or equal to "
                f"{DEFAULT_MIN_RESULTS}."
            )

        log_streams_list = (
            load_csv_to_list(log_streams_names, "Log Streams")
            if log_streams_names
            else None
        )

        if time_frame == "Custom":
            time_range = get_time_frame(start_time=start_time, end_time=end_time)
            start_time = time_range[0]
            end_time = time_range[1]
            siemplify.LOGGER.info(
                "The time range to fetch log events from is: "
                f"[{start_time}, {end_time}]"
            )
        elif time_frame:
            start_time = (
                unix_now() - TIME_FRAME_MAPPING[time_frame]
            )  # start time in milliseconds
            end_time = unix_now()  # end time in milliseconds
            siemplify.LOGGER.info(
                "The time range to fetch log events from is: "
                f"[{start_time}, {end_time}]"
            )
        else:
            start_time = None
            end_time = None

        manager = AWSCloudWatchManager(
            aws_access_key=aws_access_key,
            aws_secret_key=aws_secret_key,
            aws_default_region=aws_default_region,
        )

        siemplify.LOGGER.info(
            f"Fetching log events from {INTEGRATION_DISPLAY_NAME} service"
        )
        log_events = manager.search_log_events(
            log_group=log_group_name,
            log_streams=log_streams_list,
            start_time=start_time,
            end_time=end_time,
            custom_filter=custom_filter,
            max_events_to_return=max_events_to_return,
        )
        siemplify.LOGGER.info(
            f"Successfully Fetched log events from {INTEGRATION_DISPLAY_NAME} service"
        )

        if log_events:
            json_results = [log_event.as_json() for log_event in log_events]
            siemplify.result.add_result_json(json_results)
            csv_list = [log_event.as_csv() for log_event in log_events]
            siemplify.result.add_data_table("Search Results", construct_csv(csv_list))
            output_message = (
                f"Successfully executed search in {INTEGRATION_DISPLAY_NAME}"
            )
            result_value = True

        else:
            output_message = "No data was found for the provided search."

        status = EXECUTION_STATE_COMPLETED

    except Exception as e:
        output_message = f"Error executing action '{SEARCH_LOG_EVENTS}'. Reason: {e}"
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
