from __future__ import annotations

import sys
import json

from typing import Any, Optional
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
)

from ..core.constants import (
    DEFAULT_TIMEOUT,
    EXECUTE_EMAIL_SCRIPT_NAME,
    FAILED_STATUS,
    INTEGRATION_DISPLAY_NAME,
    INTEGRATION_NAME,
    RATE_LIMIT_EXCEEDED,
    REJECTED_STATUS,
    RUNNING_STATUS,
    SUCCESS_STATUS,
)
from ..core.TrendVisionOneExceptions import TrendVisionOneTimeoutException
from ..core.TrendVisionOneManager import TrendVisionOneManager
from ..core.UtilsManager import is_async_action_global_timeout_approaching


def query_operation_status(
    siemplify: SiemplifyAction,
    manager: TrendVisionOneManager,
    result_data: dict,
    action_start_time: int,
    error_message: Optional[str] = None,
) -> tuple[str, Any, int]:
    """Get operation details and results to update siemplify.end attributes.

    Args:
        siemplify (SiemplifyAction): SiemplifyAction object.
        manager (TrendVisionOneManager): TrendVisionOneManager manager object.
        result_data (Dict): Result data dictionary from Execute Email.
        action_start_time (int): Action start time in milliseconds.

    Raises:
        TrendVisionOneTimeoutException: Exception to be raised if timeout
        approached.

    Returns:
        Tuple[str, Any, int]: output_message, is_success, result
    """
    results_emails = result_data.get("result_emails", {})
    for message_id, task_id in results_emails.items():
        task_details = manager.get_task_detail(
            task_id=task_id, is_execute_email_action=True
        )
        if is_async_action_global_timeout_approaching(
            siemplify, action_start_time
        ) or is_approaching_timeout(action_start_time, DEFAULT_TIMEOUT):
            raise TrendVisionOneTimeoutException(
                "action ran into a timeout during execution. "
                "Please increase the timeout in IDE."
            )

        json_data = task_details.to_json()

        task_result = task_details.raw_data.get("tasks", [])[0]
        task_status = task_result.get("status")
        task_error = task_result.get("error", {})
        error_message = task_error.get("message")

        if task_details.status == SUCCESS_STATUS:
            if message_id in result_data["pending"]:
                result_data["pending"].remove(message_id)

            if task_status == SUCCESS_STATUS and not task_error:
                siemplify.LOGGER.info(
                    "Successfully completed execute email action"
                    f" for message id: {message_id}"
                )
                if message_id not in result_data["completed"]:
                    result_data["completed"].append(message_id)
                result_data["json_results"][message_id] = json_data
            else:
                if message_id not in result_data["failed"]:
                    result_data["failed"].append(message_id)
                result_data["json_results"][message_id] = json_data

            result_data["result_emails"][message_id] = None

        elif task_details.status == RUNNING_STATUS:
            result_data["json_results"][message_id] = json_data

        elif task_details.status in [FAILED_STATUS, REJECTED_STATUS]:
            result_data["result_emails"][message_id] = None
            result_data["json_results"][message_id] = json_data
            if message_id not in result_data["failed"]:
                result_data["failed"].append(message_id)
            if message_id in result_data["pending"]:
                result_data["pending"].remove(message_id)
            if message_id in result_data["completed"]:
                result_data["completed"].remove(message_id)

    result_data["result_emails"] = {
        k: v for k, v in result_data["result_emails"].items() if v
    }

    if result_data["pending"]:
        output_message = f'Pending: {", ".join(result_data["pending"])}'
        result_value = json.dumps(result_data)

        return output_message, result_value, EXECUTION_STATE_INPROGRESS

    if result_data["failed"]:
        status = EXECUTION_STATE_FAILED
        output_message, result_value = generate_output_message_and_result(
            result_data, error_message
        )
        return output_message, result_value, EXECUTION_STATE_FAILED

    status = EXECUTION_STATE_COMPLETED
    if result_data["json_results"]:
        siemplify.LOGGER.info("adding json result")
        siemplify.result.add_result_json(
            convert_dict_to_json_result_dict(result_data["json_results"])
        )
        siemplify.LOGGER.info("Json result added.")

    output_message, result_value = generate_output_message_and_result(
        result_data, error_message
    )

    return output_message, result_value, status


def start_operation(
    siemplify: SiemplifyAction,
    manager: TrendVisionOneManager,
    action_start_time: int,
    email_action: str,
    message_id: str,
    mailbox: str,
    description: str,
) -> tuple[str, bool, int]:
    """Execute Emails in first run.

    Args:
        siemplify (SiemplifyAction): SiemplifyAction object.
        manager (TrendVisionOneManager): TrendVisionOneManager manager object.
        action_start_time (int): Action start time in milliseconds.
        email_action (str): the action for the email - quarantine/restore/delete.
        message_id (str): the ID of the message that needs to be used in the action.
        mailbox (str): the mailbox related to the message.
        description (str): a description for the performed action

    Returns:
        Tuple[str, bool, int]: output_message, is_success, result
    """
    result_data = {
        "result_emails": {},
        "json_results": {},
        "completed": [],
        "failed": [],
        "pending": [],
        "limit_exceeded": [],
    }
    error_message = None

    try:
        siemplify.LOGGER.info(
            f"Started processing {email_action} action on message id: {message_id}"
        )
        result = manager.execute_email(
            email_action=email_action,
            message_id=message_id,
            mailbox=mailbox,
            description=description,
        )
        error_message = result.error_message
        if error_message is None and result.id is not None:
            result_data["result_emails"][message_id] = result.id
            result_data["pending"].append(message_id)
        else:
            result_data["failed"].append(message_id)
            siemplify.LOGGER.info(f"Execute Email task failed for : {message_id}")
    except Exception as e:
        if error_message is None:
            error_message = str(e)
        if RATE_LIMIT_EXCEEDED in str(e):
            result_data["limit_exceeded"].append(message_id)
        else:
            result_data["failed"].append(message_id)

        siemplify.LOGGER.error(
            f"An error occurred during Execute Email for message id: {message_id}"
        )
        siemplify.LOGGER.exception(e)
    siemplify.LOGGER.info(
        f"Finished processing Execute Email for message id: {message_id}"
    )

    output_message, result_value, status = query_operation_status(
        siemplify=siemplify,
        manager=manager,
        result_data=result_data,
        action_start_time=action_start_time,
        error_message=error_message,
    )

    return output_message, result_value, status


def generate_output_message_and_result(
    result_data: dict, error_message: str = None
) -> tuple(str, bool):
    """Update output message and result based on the status for Execute Email.

    Args:
        result_data (Dict): Result data dictionary from Execute Email.
        error_message (str): error message in case the execution fails.

    Returns:
        Tuple(str, bool): output_message, is_success
    """
    result_value = True

    if result_data["completed"]:
        message_id = result_data["completed"][0]
        output_message = (
            f"Successfully executed action on the message "
            f"{message_id} in {INTEGRATION_DISPLAY_NAME}\n"
        )

    else:
        result_value = False
        output_message = (
            f"Error executing action {EXECUTE_EMAIL_SCRIPT_NAME}. "
            f"Reason: {error_message}"
        )

    return output_message, result_value


@output_handler
def main(is_first_run):
    siemplify = SiemplifyAction()
    action_start_time = unix_now()
    siemplify.script_name = EXECUTE_EMAIL_SCRIPT_NAME

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

    # Action parameters
    email_action = extract_action_param(
        siemplify, param_name="Action", is_mandatory=False, print_value=True
    )
    message_id = extract_action_param(
        siemplify, param_name="Message ID", is_mandatory=True, print_value=True
    )
    mailbox = extract_action_param(
        siemplify, param_name="Mailbox", is_mandatory=False, print_value=True
    )
    mailbox = mailbox.lower()
    description = extract_action_param(
        siemplify, param_name="Description", is_mandatory=False, print_value=True
    )

    result_value = False
    result_data = {}
    status = EXECUTION_STATE_COMPLETED

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
                email_action=email_action,
                message_id=message_id,
                mailbox=mailbox,
                description=description,
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
                error_message=None,
            )
    except TrendVisionOneTimeoutException as e:
        output_message = (
            f"Error executing action {EXECUTE_EMAIL_SCRIPT_NAME}. " f"Reason: {e}\n"
        )
        status = EXECUTION_STATE_FAILED

        if result_data:
            json_results = result_data.get("json_results", {})
            siemplify.result.add_result_json(
                convert_dict_to_json_result_dict(json_results)
            )

            output_message_for_finished, _ = generate_output_message_and_result(
                result_data
            )
            if "Reason: None" not in output_message_for_finished:
                output_message += output_message_for_finished

        result_value = False
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)

    except Exception as e:
        output_message = (
            f"Error executing action {EXECUTE_EMAIL_SCRIPT_NAME}. " f"Reason: {e}"
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
