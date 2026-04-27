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

SCRIPT_NAME = "Panorama - Get Correlated Traffic Between IPs"
PROVIDER_NAME = "Panorama"
CSV_TABLE_NAME = "Traffic Logs between {} and {}"
LOG_TYPE = "Traffic"


def start_operation(siemplify, manager):
    """
    Start operation action.
    :param siemplify: SiemplifyAction object.
    :param manager: PanoramaParser object.
    :return: {output message, json result, execution state}
    """
    # Parameters
    max_hours_backwards = extract_action_param(
        siemplify, param_name="Max Hours Backwards", print_value=True, input_type=int
    )
    max_logs_to_return = extract_action_param(
        siemplify, param_name="Max Logs to Return", print_value=True, input_type=int
    )

    source_ip = extract_action_param(
        siemplify, param_name="Source IP", print_value=True
    )
    destination_ip = extract_action_param(
        siemplify, param_name="Destination IP", print_value=True
    )

    source_ips = [ip.strip() for ip in source_ip.split(",")]
    destination_ips = [ip.strip() for ip in destination_ip.split(",")]

    failed_pairs = [
        (
            (source_ips[i : i + 1] or [None])[0],
            (destination_ips[i : i + 1] or [None])[0],
        )
        for i in range(
            min(len(source_ips), len(destination_ips)),
            max(len(source_ips), len(destination_ips)),
        )
    ]

    try:

        job_ids_with_ip_pairs = [
            (
                manager.initialize_search_log_query(
                    LOG_TYPE,
                    manager.build_query_from_ip_pair(source_ips[i], destination_ips[i]),
                    max_hours_backwards,
                    max_logs_to_return,
                ),
                (source_ips[i], destination_ips[i]),
            )
            for i in range(0, min(len(source_ips), len(destination_ips)))
        ]
        # since api return job data almost instantly here we will try to get data. If data is ready action will finish.
        return query_operation_status(
            siemplify, manager, job_ids_with_ip_pairs, failed_pairs, []
        )

    except Exception as e:
        err_msg = f"Action wasn't able to list logs. Reason: {str(e)}"
        output_message = err_msg
        siemplify.LOGGER.error(err_msg)
        siemplify.LOGGER.exception(e)
        return output_message, False, EXECUTION_STATE_COMPLETED


def query_operation_status(
    siemplify, manager, job_ids_with_ip_pairs, failed_pairs, log_entities_with_ip_pairs
):
    """
    Query operation status.
    :param siemplify: SiemplifyAction object.
    :param manager: PanoramaParser object.
    :param job_ids_with_ip_pairs: {list} The job ids with appropriate ip pairs. Ex. [(100, (10.0.0.1, 8.8.8.8))]
    :param failed_pairs: {list} Failed ip pairs. Ex. [(10.0.0.1, 8.8.8.8), (10.0.0.1, None)]
    :param log_entities_with_ip_pairs: {list} LogEntities for ip pair. Ex.  [([{entity_json}}], (10.0.0.1, 8.8.8.8))]
    :return: {output message, json result, execution state}
    """

    output_message = ""
    state = EXECUTION_STATE_INPROGRESS
    item_to_delete = []
    new_list = []
    for i in range(len(job_ids_with_ip_pairs)):
        job_id = job_ids_with_ip_pairs[i][0]

        ip_pair = job_ids_with_ip_pairs[i][1]

        try:
            log_entities = manager.get_query_result(job_id)
            if log_entities:
                log_entities_with_ip_pairs.append(
                    ([log_entity.to_json() for log_entity in log_entities], ip_pair)
                )
            else:
                failed_pairs.append(ip_pair)

        except JobNotFinishedException as e:
            new_list.append(job_ids_with_ip_pairs[i])
            output_message += (
                "Continuing processing IP pair {}.... Progress {}%\n".format(
                    f"{ip_pair[0]}-{ip_pair[1]}", e.progress
                )
            )

    job_ids_with_ip_pairs = new_list

    result_value = json.dumps(
        [job_ids_with_ip_pairs, failed_pairs, log_entities_with_ip_pairs]
    )

    if not job_ids_with_ip_pairs:
        state = EXECUTION_STATE_COMPLETED
        if log_entities_with_ip_pairs:
            result_value = True
            output_message += (
                "Successfully listed correlated logs for the following pairs of Source and Destination "
                "IPs:{}\n".format(
                    "\n.".join(
                        [
                            f"{log_entity_with_ip_pair[1][0]} - {log_entity_with_ip_pair[1][1]}"
                            for log_entity_with_ip_pair in log_entities_with_ip_pairs
                        ]
                    )
                )
            )

            json_result = []

            for log_entities_with_ip_pair in log_entities_with_ip_pairs:
                log_entities = manager.get_log_entities_from_json(
                    log_entities_with_ip_pair[0]
                )
                json_result += [log_entity.to_json() for log_entity in log_entities]
                siemplify.result.add_data_table(
                    CSV_TABLE_NAME.format(
                        log_entities_with_ip_pair[1][0], log_entities_with_ip_pair[1][1]
                    ),
                    construct_csv(
                        [log_entity.to_csv(LOG_TYPE) for log_entity in log_entities]
                    ),
                )
            siemplify.result.add_result_json(json_result)
        else:
            result_value = False
            output_message += "No correlated network traffic logs were found.\n"

        if failed_pairs:
            output_message += "Unable to list correlated logs for the following pairs of Source and Destination IPs:{}".format(
                "\n.".join(
                    [
                        f"{failed_pair[0]} - {failed_pair[1]}"
                        for failed_pair in failed_pairs
                    ]
                )
            )

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

    siemplify.LOGGER.info(f"----------------- {mode} - Started -----------------")

    try:
        manager = PanoramaManager(api_root, username, password, verify_ssl)

        if is_first_run:
            output_message, result_value, status = start_operation(siemplify, manager)
        else:

            job_ids_with_ip_pairs, failed_pairs, log_entities_with_ip_pairs = (
                json.loads(siemplify.parameters["additional_data"])
            )
            output_message, result_value, status = query_operation_status(
                siemplify,
                manager,
                job_ids_with_ip_pairs,
                failed_pairs,
                log_entities_with_ip_pairs,
            )

    except Exception as e:
        msg = f"Error executing action 'Get Correlated Traffic Between IPs'. Reason: {str(e)}"
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
