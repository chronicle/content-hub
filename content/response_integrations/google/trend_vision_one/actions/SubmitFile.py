from __future__ import annotations

import sys
import json
from typing import Any

from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import convert_dict_to_json_result_dict, output_handler, unix_now
from soar_sdk.ScriptResult import (
    EXECUTION_STATE_COMPLETED,
    EXECUTION_STATE_FAILED,
    EXECUTION_STATE_INPROGRESS,
)
from TIPCommon import (
    extract_action_param,
    extract_configuration_param,
    is_approaching_timeout,
    string_to_multi_value,
)

from ..core.constants import (
    DEFAULT_TIMEOUT,
    FAILED_STATUS,
    INTEGRATION_DISPLAY_NAME,
    INTEGRATION_NAME,
    RATE_LIMIT_EXCEEDED,
    REJECTED_STATUS,
    RUNNING_STATUS,
    SUBMIT_FILE_SCRIPT_NAME,
    SUCCESS_STATUS,
)
from ..core.TrendVisionOneExceptions import TrendVisionOneTimeoutException
from ..core.TrendVisionOneManager import TrendVisionOneManager
from ..core.UtilsManager import (
    check_submit_files_in_system,
    is_async_action_global_timeout_approaching,
)


def start_operation(
    siemplify: SiemplifyAction,
    manager: TrendVisionOneManager,
    action_start_time: int,
    file_paths: str,
    archive_password: str,
    document_password: str,
    arguments: str,
) -> tuple[str, bool, int]:
    """Submit file in first run.

    Args:
        siemplify (SiemplifyAction): SiemplifyAction object.
        manager (TrendVisionOneManager): TrendVisionOneManager manager object.
        action_start_time (int): Action start time in milliseconds.
        file_paths (str): file path as CSV provided in parameter.
        archive_password (str): archive password if file is an archive.
        document_password (str): document password if file is a document.
        arguments (str): argument passed to a file if file is a executable.

    Raises:
        IOError: Exception raised If any of the file is not present in
        filesystem.

    Returns:
        Tuple[str, bool, int]: output_message, is_success, result
    """
    result_data = {
        "result_file_paths": {},
        "json_results": {},
        "completed": [],
        "failed": [],
        "pending": [],
        "limit_exceeded": [],
    }

    file_paths_list = string_to_multi_value(file_paths, only_unique=True)
    not_found_files = check_submit_files_in_system(file_paths_list)
    if not_found_files:
        raise IOError(
            "the following files weren't found or not accessible: "
            f'{", ".join(not_found_files)}'
        )
    for file_path in file_paths_list:
        siemplify.LOGGER.info(f"Started processing file: {file_path}")
        try:
            result = manager.submit_file(
                file_path=file_path,
                archive_password=archive_password,
                document_password=document_password,
                arguments=arguments,
            )

            if result:
                result_data["result_file_paths"][file_path] = result.id
                result_data["pending"].append(file_path)

            else:
                result_data["failed"].append(file_path)
                siemplify.LOGGER.info(f"Submit file task failed for : {file_path}")

        except Exception as e:
            if RATE_LIMIT_EXCEEDED in str(e):
                result_data["limit_exceeded"].append(file_path)
            else:
                result_data["failed"].append(file_path)

            siemplify.LOGGER.error(f"An error occurred during submit file {file_path}")
            siemplify.LOGGER.exception(e)

        siemplify.LOGGER.info(f"Finished processing file: {file_path}")

    output_message, result_value, status = query_operation_status(
        siemplify, manager, result_data, action_start_time
    )

    return output_message, result_value, status


def query_operation_status(
    siemplify: SiemplifyAction,
    manager: TrendVisionOneManager,
    result_data: dict,
    action_start_time: int,
) -> tuple[str, Any, int]:
    """Get operation details and results to update siemplify.end attributes.

    Args:
        siemplify (SiemplifyAction): SiemplifyAction object.
        manager (TrendVisionOneManager): TrendVisionOneManager manager object.
        result_data (Dict): Result data dictionary from submit file.
        action_start_time (int): Action start time in milliseconds.

    Raises:
        TrendVisionOneTimeoutException: Exception to be raised if timeout
        approached.

    Returns:
        Tuple[str, Any, int]: output_message, is_success, result
    """
    results_paths = result_data["result_file_paths"]
    for file_path, task_id in results_paths.items():
        task_details = manager.get_task_detail(task_id=task_id)
        if is_async_action_global_timeout_approaching(
            siemplify, action_start_time
        ) or is_approaching_timeout(action_start_time, DEFAULT_TIMEOUT):
            raise TrendVisionOneTimeoutException(
                "action ran into a timeout during execution. "
                f'Pending files: {", ".join(result_data["pending"])}.'
            )

        json_data = task_details.to_json()
        if task_details.status == SUCCESS_STATUS:
            result_data["pending"].remove(file_path)
            task_result = manager.get_task_result(task_id=task_details.id)

            if task_result:
                siemplify.LOGGER.info(f"Successfully submitted file {file_path}")
                result_data["completed"].append(file_path)
                result_data["json_results"][file_path] = task_result
            else:
                result_data["failed"].append(file_path)
                result_data["json_results"][file_path] = json_data

            result_data["result_file_paths"][file_path] = None

        elif task_details.status == RUNNING_STATUS:
            result_data["json_results"][file_path] = json_data

        elif task_details.status in [FAILED_STATUS, REJECTED_STATUS]:
            result_data["result_file_paths"][file_path] = None
            result_data["json_results"][file_path] = json_data
            result_data["failed"].append(file_path)
            result_data["pending"].remove(file_path)

    result_data["result_file_paths"] = {
        k: v for k, v in result_data["result_file_paths"].items() if v
    }

    if result_data["pending"]:
        output_message = (
            f'Pending file submissions: {", ".join(result_data["pending"])}'
        )
        result_value = json.dumps(result_data)

        return output_message, result_value, EXECUTION_STATE_INPROGRESS

    status = EXECUTION_STATE_COMPLETED
    if result_data["json_results"]:
        siemplify.LOGGER.info("adding json result")
        siemplify.result.add_result_json(
            convert_dict_to_json_result_dict(result_data["json_results"])
        )
        siemplify.LOGGER.info("Json result added.")

    output_message, result_value = generate_output_message_and_result(result_data)

    return output_message, result_value, status


def generate_output_message_and_result(result_data: dict) -> tuple(str, bool):
    """Update output message and result based on the status for submit files.

    Args:
        result_data (Dict): Result data dictionary from submit file.

    Returns:
        Tuple(str, bool): output_message, is_success
    """
    result_value = True
    limit_message = (
        "Action wasn't able to submit all files as the daily quota was "
        "reached during the execution. Pending files: {pending_files}"
    )
    pending_files = ", ".join(result_data["limit_exceeded"])

    if (
        result_data["limit_exceeded"]
        and not result_data["completed"]
        and not result_data["failed"]
    ):
        result_value = False
        output_message = limit_message.format(pending_files=pending_files)

        return output_message, result_value

    if result_data["completed"]:
        completed_submit_files = ", ".join(
            [entity for entity in result_data["completed"]]
        )
        output_message = (
            "Successfully submitted the following files in "
            f"{INTEGRATION_DISPLAY_NAME}: {completed_submit_files}\n"
        )

        if result_data["failed"]:
            result_value = False
            failed_submission = ", ".join([entity for entity in result_data["failed"]])
            output_message += (
                "Action wasn't able to retrieve details for the following "
                f"files in {INTEGRATION_DISPLAY_NAME}: {failed_submission}\n"
            )

        if result_data["limit_exceeded"]:
            output_message += limit_message.format(pending_files=pending_files)

    else:
        output_message = "No results were found for the submitted files."
        result_value = False

    return output_message, result_value


@output_handler
def main(is_first_run):
    siemplify = SiemplifyAction()
    action_start_time = unix_now()
    siemplify.script_name = SUBMIT_FILE_SCRIPT_NAME

    siemplify.LOGGER.info("---------------- Main - Param Init ----------------")

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
    file_paths = extract_action_param(
        siemplify, param_name="File Paths", is_mandatory=True, print_value=True
    )
    archive_password = extract_action_param(
        siemplify,
        param_name="Archive Password",
        remove_whitespaces=False,
        is_mandatory=False,
    )
    document_password = extract_action_param(
        siemplify,
        param_name="Document Password",
        remove_whitespaces=False,
        is_mandatory=False,
    )
    arguments = extract_action_param(
        siemplify, param_name="Arguments", is_mandatory=False, print_value=True
    )
    result_value = False
    result_data = {}
    status = EXECUTION_STATE_COMPLETED
    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    try:
        manager = TrendVisionOneManager(
            api_root=api_root,
            api_token=api_token,
            verify_ssl=verify_ssl,
            siemplify=siemplify,
        )
        manager.test_connectivity()

        if is_first_run:
            output_message, result_value, status = start_operation(
                siemplify=siemplify,
                manager=manager,
                action_start_time=action_start_time,
                file_paths=file_paths,
                archive_password=archive_password,
                document_password=document_password,
                arguments=arguments,
            )
        else:
            result_data = json.loads(
                extract_action_param(
                    siemplify, param_name="additional_data", default_value="{}"
                )
            )
            output_message, result_value, status = query_operation_status(
                siemplify=siemplify,
                manager=manager,
                result_data=result_data,
                action_start_time=action_start_time,
            )

    except TrendVisionOneTimeoutException as e:
        output_message = (
            f"Error executing action {SUBMIT_FILE_SCRIPT_NAME}. " f"Reason: {e}. "
        )
        output_message += "Please increase the timeout in IDE.\n"
        status = EXECUTION_STATE_FAILED

        if result_data:
            json_results = result_data.get("json_results", {})
            siemplify.result.add_result_json(
                convert_dict_to_json_result_dict(json_results)
            )

            output_message_for_finished, _ = generate_output_message_and_result(
                result_data
            )
            output_message += output_message_for_finished

        result_value = False
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)

    except Exception as e:
        output_message = (
            f"Error executing action {SUBMIT_FILE_SCRIPT_NAME}. " f"Reason: {e}"
        )
        status = EXECUTION_STATE_FAILED
        result_value = False
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}"
        f"\n  is_success: {result_value}"
        f"\n  output_message: {output_message}"
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    is_first_run = len(sys.argv) < 3 or sys.argv[2] == "True"
    main(is_first_run)
