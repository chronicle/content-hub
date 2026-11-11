from __future__ import annotations
import json
import sys
from typing import Any

from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.ScriptResult import (
    EXECUTION_STATE_COMPLETED,
    EXECUTION_STATE_FAILED,
    EXECUTION_STATE_INPROGRESS,
)
from soar_sdk.SiemplifyAction import SiemplifyAction

from TIPCommon import extract_action_param, extract_configuration_param
from forti_analyzer.core.FortiAnalyzerManager import FortiAnalyzerManager
from forti_analyzer.core.UtilsManager import get_timestamps
from forti_analyzer.core.constants import (
    DEFAULT_LOGS_COUNT,
    INTEGRATION_DISPLAY_NAME,
    INTEGRATION_NAME,
    LOG_TYPES,
    MAX_PROGRESS_PERCENTAGE,
    SEARCH_LOGS_SCRIPT_NAME,
    TIME_FRAME_DEFAULT_VALUE,
    TIME_ORDER,
)


def create_search_task(
    siemplify: Any,
    manager: "FortiAnalyzerManager",
    log_type: str,
    is_case_sensitive: bool,
    query: str,
    device_id: str,
    start_time: str,
    end_time: str,
    time_order: str,
    logs_to_return: int,
) -> Any:
    """
    Function creates search task with provided parameters
    Args:
        siemplify: siemplify instance
        manager: FortiAnalyzerManager
        log_type: which type of logs to search
        is_case_sensitive: makes search query case-sensitive
        query: search query
        device_id: device id
        start_time: search for logs from date
        end_time: search for logs by date
        time_order: log ordering(asc/desc)
        logs_to_return: count of logs to return
    Returns:
        Log object
    """
    task_id = manager.create_search_task(
        log_type=log_type,
        is_case_sensitive=is_case_sensitive,
        query=query,
        device_id=device_id,
        start_time=start_time,
        end_time=end_time,
        time_order=time_order,
    )
    return search_logs(siemplify, manager, task_id, logs_to_return)


def search_logs(siemplify, manager, task_id, logs_to_return) -> Any:
    """
    Function searches logs on FortiAnalyzer
    Args:
        siemplify: Siemplify instance
        manager: FortiAnalyzerManager
        task_id: Task ID
        logs_to_return: Count of logs to return
    Returns:
        Output message, result_value, status
    """
    json_results = []
    result_value = True
    progress, results = manager.search_logs(task_id, logs_to_return)
    if progress == MAX_PROGRESS_PERCENTAGE:
        if results:
            json_results = [result.to_json() for result in results]
            status = EXECUTION_STATE_COMPLETED

            output_message = f"Successfully retrieved logs for the provided criteria in {INTEGRATION_DISPLAY_NAME}."
        else:
            status = EXECUTION_STATE_COMPLETED
            output_message = f"No logs were found for the provided criteria in {INTEGRATION_DISPLAY_NAME}."
        siemplify.result.add_result_json(json_results)
    else:
        result_value = json.dumps(
            {
                "task_id": task_id,
                "session_id": manager.api_session,
            }
        )
        status = EXECUTION_STATE_INPROGRESS
        output_message = f"Waiting for search task to be created."
    return output_message, result_value, status


@output_handler
def main(is_first_run: bool) -> None:
    siemplify = SiemplifyAction()
    siemplify.script_name = SEARCH_LOGS_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Root",
        is_mandatory=True,
        print_value=True,
    )
    username = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Username",
        is_mandatory=True,
        print_value=True,
    )
    password = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Password",
        is_mandatory=True,
        remove_whitespaces=False,
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        is_mandatory=True,
        input_type=bool,
        print_value=True,
    )

    # action parameters
    log_type = extract_action_param(
        siemplify,
        param_name="Log Type",
        print_value=True,
        is_mandatory=False,
        default_value="Traffic",
    )
    is_case_sensitive = extract_action_param(
        siemplify,
        param_name="Case Sensitive Filter",
        print_value=True,
        is_mandatory=False,
        default_value=False,
        input_type=bool,
    )
    query = extract_action_param(
        siemplify, param_name="Query Filter", print_value=True, is_mandatory=False
    )
    device_id = extract_action_param(
        siemplify,
        param_name="Device ID",
        print_value=True,
        is_mandatory=False,
        default_value="All_Fortigate",
    )

    time_frame = extract_action_param(
        siemplify,
        param_name="Time Frame",
        print_value=True,
        is_mandatory=False,
        default_value=TIME_FRAME_DEFAULT_VALUE,
    )
    start_time = extract_action_param(
        siemplify, param_name="Start Time", print_value=True, is_mandatory=False
    )
    end_time = extract_action_param(
        siemplify, param_name="End Time", print_value=True, is_mandatory=False
    )
    time_order = extract_action_param(
        siemplify,
        param_name="Time Order",
        print_value=True,
        is_mandatory=False,
        default_value="DESC",
    )
    logs_to_return = extract_action_param(
        siemplify,
        param_name="Max Logs To Return",
        print_value=True,
        input_type=int,
        is_mandatory=False,
        default_value=DEFAULT_LOGS_COUNT,
    )
    additional_data = json.loads(
        extract_action_param(
            siemplify=siemplify, param_name="additional_data", default_value="{}"
        )
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    manager = None
    result_value = True
    output_message = ""
    status = EXECUTION_STATE_INPROGRESS

    try:
        if logs_to_return < 1 or logs_to_return > 1000:
            raise Exception("Please provide valid integer between 1 and 1000.")
        session_id: str= additional_data.get("session_id")
        manager = FortiAnalyzerManager(
            api_root=api_root,
            username=username,
            password=password,
            verify_ssl=verify_ssl,
            siemplify_logger=siemplify.LOGGER,
            session_id=session_id
        )

        if is_first_run:
            start_time, end_time = get_timestamps(time_frame, start_time, end_time)
            output_message, result_value, status = create_search_task(
                siemplify=siemplify,
                manager=manager,
                log_type=LOG_TYPES[log_type],
                is_case_sensitive=is_case_sensitive,
                query=query,
                device_id=device_id,
                start_time=start_time,
                end_time=end_time,
                time_order=TIME_ORDER[time_order],
                logs_to_return=logs_to_return,
            )
        else:
            output_message, result_value, status = search_logs(
                siemplify=siemplify,
                manager=manager,
                logs_to_return=logs_to_return,
                task_id=additional_data.get("task_id"),
            )

    except Exception as e:
        siemplify.LOGGER.error(
            f"General error performing action {SEARCH_LOGS_SCRIPT_NAME}"
        )
        siemplify.LOGGER.exception(e)
        result_value = False
        status = EXECUTION_STATE_FAILED
        output_message = (
            f"Error executing action {SEARCH_LOGS_SCRIPT_NAME}. Reason: {e}"
        )
    finally:
        try:
            if manager and status != EXECUTION_STATE_INPROGRESS:
                manager.logout()
                siemplify.LOGGER.info(
                    f"Successfully logged out from {INTEGRATION_DISPLAY_NAME}"
                )
        except Exception as e:
            siemplify.LOGGER.error(f"Logging out failed. Error: {e}")
            siemplify.LOGGER.exception(e)

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"Result: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")

    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    is_first_run = len(sys.argv) < 3 or sys.argv[2] == "True"
    main(is_first_run)
