from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyAction import SiemplifyAction
from ..core.PanoramaManager import PanoramaManager
from soar_sdk.ScriptResult import (
    EXECUTION_STATE_COMPLETED,
    EXECUTION_STATE_FAILED,
    EXECUTION_STATE_INPROGRESS,
)
from TIPCommon import extract_configuration_param, extract_action_param, construct_csv
import sys
import json
from ..core.PanoramaExceptions import JobNotFinishedException

SCRIPT_NAME = "Panorama - SearchLogs"
PROVIDER_NAME = "Panorama"
CSV_TABLE_NAME = "{} Logs"


def start_operation(siemplify, manager, log_type, query):
    """
    Start operation action.
    :param siemplify: SiemplifyAction object.
    :param manager: PanoramaParser object.
    :param log_type: {str} Specify which log type should be returned.
    :param query: {str} Specify what query filter should be used to return logs.
    :return: {output message, json result, execution state}
    """
    # Parameters
    max_hours_backwards = extract_action_param(
        siemplify, param_name="Max Hours Backwards", print_value=True, input_type=int
    )
    max_logs_to_return = extract_action_param(
        siemplify, param_name="Max Logs to Return", print_value=True, input_type=int
    )

    try:
        job_id = manager.initialize_search_log_query(
            log_type, query, max_hours_backwards, max_logs_to_return
        )
        # since api return job data almost instantly here we will try to get data. If data is ready action will finish.
        return query_operation_status(siemplify, manager, job_id, log_type, query)

    except Exception as e:
        err_msg = f"Action wasn't able to list logs. Reason: {str(e)}"
        output_message = err_msg
        siemplify.LOGGER.error(err_msg)
        siemplify.LOGGER.exception(e)
        return output_message, False, EXECUTION_STATE_COMPLETED


def query_operation_status(siemplify, manager, job_id, log_type, query):
    """
    Query operation status.
    :param siemplify: SiemplifyAction object.
    :param manager: PanoramaParser object.
    :param job_id: {str} The job id to fetch data.
    :param log_type: {str} Specify which log type should be returned.
    :param query: {str} Specify what query filter should be used to return logs.
    :return: {output message, json result, execution state}
    """

    try:
        log_entities = manager.get_query_result(job_id)
        if log_entities:
            output_message = (
                f"Successfully listed {log_type} logs.  Used query: '{query}'"
            )
            result_value = True
            siemplify.result.add_result_json(
                [log_entity.to_json() for log_entity in log_entities]
            )
            siemplify.result.add_data_table(
                CSV_TABLE_NAME.format(log_type),
                construct_csv(
                    [log_entity.to_csv(log_type) for log_entity in log_entities]
                ),
            )
        else:
            output_message = f"No {log_type} logs were found. Used query: '{query}'"
            result_value = False
        state = EXECUTION_STATE_COMPLETED
    except JobNotFinishedException as e:
        output_message = f"Continuing processing query.... Progress {e.progress}%"
        result_value = json.dumps(job_id)
        state = EXECUTION_STATE_INPROGRESS

    return output_message, result_value, state


@output_handler
def main(is_first_run):
    siemplify = SiemplifyAction()
    siemplify.script_name = SCRIPT_NAME
    mode = "Main" if is_first_run else "QueryState"

    siemplify.LOGGER.info(f"----------------- {mode} - Param Init -----------------")

    # Configuration.
    api_root = extract_configuration_param(
        siemplify, provider_name=PROVIDER_NAME, param_name="Api Root"
    )
    username = extract_configuration_param(
        siemplify, provider_name=PROVIDER_NAME, param_name="Username"
    )
    password = extract_configuration_param(
        siemplify, provider_name=PROVIDER_NAME, param_name="Password"
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=PROVIDER_NAME,
        param_name="Verify SSL",
        default_value=True,
        input_type=bool,
    )

    # Parameters
    log_type = extract_action_param(
        siemplify,
        param_name="Log Type",
        input_type=str,
        is_mandatory=True,
        print_value=True,
    )
    query = extract_action_param(siemplify, param_name="Query", print_value=True)
    siemplify.LOGGER.info(f"----------------- {mode} - Started -----------------")

    try:
        manager = PanoramaManager(api_root, username, password, verify_ssl)

        if is_first_run:
            output_message, result_value, status = start_operation(
                siemplify, manager, log_type, query
            )
        else:
            job_id = json.loads(siemplify.parameters["additional_data"])
            output_message, result_value, status = query_operation_status(
                siemplify, manager, job_id, log_type, query
            )

    except Exception as e:
        msg = f"Error executing action 'Search Logs'. Reason: {str(e)}"
        siemplify.LOGGER.error(msg)
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        result_value = False
        output_message = msg

    siemplify.LOGGER.info(f"----------------- {mode} - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  result_value: {result_value}\n  output_message: {output_message}"
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    is_first_run = len(sys.argv) < 3 or sys.argv[2] == "True"
    main(is_first_run)
