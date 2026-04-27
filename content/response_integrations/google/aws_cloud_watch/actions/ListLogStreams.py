from __future__ import annotations
from ..core.AWSCloudWatchManager import AWSCloudWatchManager
from TIPCommon import extract_configuration_param, extract_action_param, construct_csv
from ..core.consts import (
    INTEGRATION_DISPLAY_NAME,
    LIST_LOG_STREAMS,
    SORTING_MAPPING,
    DEFAULT_MIN_RESULTS,
    ORDER_BY_MAPPING,
)
from ..core.exceptions import (
    AWSCloudWatchInvalidParameterException,
    AWSCloudWatchResourceNotFoundException,
)
from ..core.utils import load_csv_to_list

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = f"{INTEGRATION_DISPLAY_NAME} - {LIST_LOG_STREAMS}"
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

    log_groups = extract_action_param(
        siemplify, param_name="Log Groups", is_mandatory=True, print_value=True
    )

    order_by = extract_action_param(
        siemplify, param_name="Order By", is_mandatory=False, print_value=True
    )

    order_by = ORDER_BY_MAPPING[order_by]

    sort_order = extract_action_param(
        siemplify, param_name="Sort Order", is_mandatory=False, print_value=True
    )

    sort_order = SORTING_MAPPING[sort_order]

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    json_results = []
    success_log_groups = []
    not_found_log_groups = []
    output_message = ""
    result_value = False

    try:
        manager = AWSCloudWatchManager(
            aws_access_key=aws_access_key,
            aws_secret_key=aws_secret_key,
            aws_default_region=aws_default_region,
        )

        max_streams_to_return = extract_action_param(
            siemplify,
            param_name="Max Streams To Return",
            input_type=int,
            is_mandatory=False,
            print_value=True,
            default_value=50,
        )

        if max_streams_to_return < DEFAULT_MIN_RESULTS:
            raise AWSCloudWatchInvalidParameterException(
                f"'Max Streams to Return' should be greater than "
                f"{DEFAULT_MIN_RESULTS}."
            )

        log_groups_list = load_csv_to_list(log_groups, "Log Groups")

        for log_group in log_groups_list:
            try:
                siemplify.LOGGER.info(
                    f"Fetching Log Streams from {INTEGRATION_DISPLAY_NAME}..."
                )
                log_streams_list = manager.list_log_streams(
                    log_group_name=log_group,
                    order_by=order_by,
                    sort_order=sort_order,
                    max_streams_to_return=max_streams_to_return,
                )
                siemplify.LOGGER.info(
                    f"Successfully fetched Log Streams of log group {log_group} from "
                    f"{INTEGRATION_DISPLAY_NAME}."
                )

                if log_streams_list:
                    success_log_groups.append(log_group)
                    siemplify.LOGGER.info(
                        f"Creating JSON and CSV table from the data of {log_group} log "
                        "group..."
                    )

                    json_results.append(
                        [
                            {
                                "group": log_group,
                                "logStreams": [
                                    log_stream.as_json()
                                    for log_stream in log_streams_list
                                ],
                            }
                        ]
                    )

                    csv_list = [log_stream.as_csv() for log_stream in log_streams_list]
                    siemplify.result.add_data_table(
                        f"{log_group}: Log Streams", construct_csv(csv_list)
                    )

                    siemplify.LOGGER.info(
                        "Successfully created JSON and CSV table from the data of "
                        f"{log_group} log group..."
                    )

            except AWSCloudWatchResourceNotFoundException as error:
                siemplify.LOGGER.error(error)
                not_found_log_groups.append(log_group)

        if success_log_groups:
            result_value = True
            siemplify.result.add_result_json(json_results)
            output_message += (
                "Successfully returned available log streams for the following log "
                f"groups in AWS CloudWatch: {', '.join(success_log_groups)}\n"
            )

            if not_found_log_groups:
                output_message += (
                    "Action wasn't able to return available log streams for the "
                    "following log groups in AWS CloudWatch: "
                    f"{', '.join(not_found_log_groups)}\n"
                )

        else:
            output_message += (
                "No log streams were found for the provided log groups in AWS "
                "CloudWatch\n"
            )

        status = EXECUTION_STATE_COMPLETED

    except Exception as e:
        output_message = f"Error executing action '{LIST_LOG_STREAMS}'. Reason: {e}"
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
