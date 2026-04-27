from __future__ import annotations
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from ..core.CheckpointManager import CheckpointManager
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from TIPCommon import extract_configuration_param, extract_action_param, construct_csv
from ..core.constants import (
    INTEGRATION_NAME,
    SHOW_LOGS_SCRIPT_NAME,
    RESULTS_CSV_NAME,
    TIME_FRAME_MAPPING,
    LOG_MAPPING,
    INVALID_PARAMETERS_CODE,
)
from ..core.exceptions import CheckpointManagerBadRequestException


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = SHOW_LOGS_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    # INIT INTEGRATION CONFIGURATION:
    server_address = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Server Address",
        is_mandatory=True,
    )
    username = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Username",
        is_mandatory=True,
    )
    password = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Password",
        is_mandatory=True,
    )
    domain_name = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Domain",
        is_mandatory=False,
        default_value="",
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        default_value=False,
        input_type=bool,
    )

    query_filter = extract_action_param(
        siemplify, param_name="Query Filter", print_value=True
    )
    time_frame = extract_action_param(
        siemplify, param_name="Time Frame", is_mandatory=True, print_value=True
    )
    log_type = extract_action_param(
        siemplify, param_name="Log Type", is_mandatory=True, print_value=True
    )
    max_logs_limit = extract_action_param(
        siemplify,
        param_name="Max Logs To Return",
        input_type=int,
        default_value=50,
        print_value=True,
    )

    output_message = "Successfully retrieved logs from Checkpoint FireWall!"
    result_value = True
    status = EXECUTION_STATE_COMPLETED

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    try:
        manager = CheckpointManager(
            server_address=server_address,
            username=username,
            password=password,
            domain=domain_name,
            verify_ssl=verify_ssl,
        )
        # Get Logs
        logs = manager.get_logs(
            query_filter=query_filter,
            time_frame=TIME_FRAME_MAPPING[time_frame],
            log_type=LOG_MAPPING[log_type],
            max_logs_limit=max_logs_limit,
        )
        if logs:
            # Add data to table
            siemplify.result.add_data_table(
                title=RESULTS_CSV_NAME,
                data_table=construct_csv(
                    [log.to_csv(log_type=LOG_MAPPING[log_type]) for log in logs]
                ),
            )
            # Add json result
            siemplify.result.add_result_json([log.to_json() for log in logs])

        manager.log_out()
    except CheckpointManagerBadRequestException as err:
        output_message = f"Action wasn't able to retrieve logs from Checkpoint FireWall! Reason: {err}. Code: {INVALID_PARAMETERS_CODE}"
        result_value = False
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(err)

    except Exception as err:
        output_message = (
            f"Error executing action {SHOW_LOGS_SCRIPT_NAME}. Reason: {err}"
        )
        status = EXECUTION_STATE_FAILED
        result_value = False
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(err)

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  result_value: {result_value}\n  output_message: {output_message}"
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
