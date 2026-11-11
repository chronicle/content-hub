from __future__ import annotations
import json
import sys
from soar_sdk.SiemplifyUtils import output_handler, unix_now
from soar_sdk.ScriptResult import (
    EXECUTION_STATE_COMPLETED,
    EXECUTION_STATE_FAILED,
    EXECUTION_STATE_INPROGRESS,
)
from soar_sdk.SiemplifyAction import SiemplifyAction
from TIPCommon import extract_configuration_param, extract_action_param
from tanium.core.TaniumManager import TaniumManager
from tanium.core.constants import (
    INTEGRATION_NAME,
    GET_TASK_DETAILS_SCRIPT_NAME,
    TASK_STATUS_COMPLETED,
    TASK_STATUS_INCOMPLETE,
    TASK_STATUS_ERROR,
    DEFAULT_TIMEOUT,
)
from tanium.core.utils import (
    is_async_action_global_timeout_approaching,
    is_approaching_process_timeout,
    convert_comma_separated_to_list,
)


def check_data(siemplify, manager, action_start_time, result_data, wait_for_completion):
    timeout_approaching = False
    completed_tasks = result_data.get("completed", [])
    pending_tasks = result_data.get("pending", [])
    failed_tasks = result_data.get("failed", [])
    json_results = result_data.get("json_results", [])

    for task_id in pending_tasks:
        if is_async_action_global_timeout_approaching(
            siemplify, action_start_time
        ) or is_approaching_process_timeout(action_start_time, DEFAULT_TIMEOUT):
            siemplify.LOGGER.info("Timeout is approaching. Action will gracefully exit")
            timeout_approaching = True
            break

        siemplify.LOGGER.info(f"Getting details for task with id {task_id}.")
        try:
            task_details = manager.get_task_details(task_id=task_id)

            if task_details:
                if wait_for_completion and task_details.status not in [
                    TASK_STATUS_COMPLETED,
                    TASK_STATUS_INCOMPLETE,
                    TASK_STATUS_ERROR,
                ]:
                    continue
                completed_tasks.append(task_id)
                json_results.append(task_details.to_json())
            else:
                failed_tasks.append(task_id)
        except Exception as err:
            failed_tasks.append(task_id)
            siemplify.LOGGER.error(f"An error occurred on task with id {task_id}")
            siemplify.LOGGER.exception(err)

    pending_tasks = [
        t for t in pending_tasks if t not in completed_tasks and t not in failed_tasks
    ]
    result_data = {
        "completed": completed_tasks,
        "pending": pending_tasks,
        "failed": failed_tasks,
        "json_results": json_results,
    }

    if wait_for_completion and pending_tasks:
        status = EXECUTION_STATE_INPROGRESS
        result_value = json.dumps(result_data)
        output_message = f"Fetching details about tasks: {', '.join(pending_tasks)}"
    else:
        output_message, result_value, status = finish_operation(
            siemplify=siemplify,
            result_data=result_data,
            timeout_approaching=timeout_approaching,
        )

    return output_message, result_value, status


def finish_operation(siemplify, result_data, timeout_approaching):
    result_value = True
    status = EXECUTION_STATE_COMPLETED
    completed_tasks = result_data.get("completed", [])
    pending_tasks = result_data.get("pending", [])
    failed_tasks = result_data.get("failed", [])
    json_results = result_data.get("json_results", [])
    output_message = ""

    if completed_tasks:
        output_message += (
            f"Successfully fetched details about the following tasks in {INTEGRATION_NAME}: "
            f"{', '.join(completed_tasks)}. \n"
        )
        siemplify.result.add_result_json(json_results)
    if failed_tasks:
        output_message += (
            f"Action wasn't able to find the following tasks in {INTEGRATION_NAME}: "
            f"{', '.join(failed_tasks)} \n"
        )
    if timeout_approaching and pending_tasks:
        raise Exception(
            f"action ran into a timeout during execution. Pending tasks: {', '.join(pending_tasks)}. "
            f"Please increase the timeout in IDE.\n"
        )
    if not completed_tasks:
        output_message = f"No tasks were found in {INTEGRATION_NAME}."
        result_value = False

    return output_message, result_value, status


@output_handler
def main(is_first_run):
    siemplify = SiemplifyAction()
    action_start_time = unix_now()
    siemplify.script_name = GET_TASK_DETAILS_SCRIPT_NAME
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
        remove_whitespaces=False,
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        input_type=bool,
        print_value=True,
    )

    # Action parameters
    task_ids = extract_action_param(
        siemplify, param_name="Task IDs", is_mandatory=True, print_value=True
    )
    wait_for_completion = extract_action_param(
        siemplify, param_name="Wait For Completion", input_type=bool, print_value=True
    )

    additional_data = json.loads(
        extract_action_param(
            siemplify=siemplify, param_name="additional_data", default_value="{}"
        )
    )
    task_ids = convert_comma_separated_to_list(task_ids)

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    try:
        manager = TaniumManager(
            api_root=api_root,
            api_token=api_token,
            verify_ssl=verify_ssl,
            force_check_connectivity=True,
            logger=siemplify.LOGGER,
        )

        if is_first_run:
            output_message, result_value, status = check_data(
                siemplify=siemplify,
                manager=manager,
                action_start_time=action_start_time,
                result_data={"pending": task_ids},
                wait_for_completion=wait_for_completion,
            )
        else:
            output_message, result_value, status = check_data(
                siemplify=siemplify,
                manager=manager,
                action_start_time=action_start_time,
                result_data=additional_data,
                wait_for_completion=wait_for_completion,
            )

    except Exception as e:
        siemplify.LOGGER.error(
            f"General error performing action {GET_TASK_DETAILS_SCRIPT_NAME}"
        )
        siemplify.LOGGER.exception(e)
        result_value = False
        status = EXECUTION_STATE_FAILED
        output_message = (
            f"Error executing action {GET_TASK_DETAILS_SCRIPT_NAME}. Reason: {e}"
        )

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"Result: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")

    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    is_first_run = len(sys.argv) < 3 or sys.argv[2] == "True"
    main(is_first_run)
