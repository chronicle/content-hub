from __future__ import annotations

import json
import sys
from typing import Tuple, Any

from soar_sdk.ScriptResult import (
    EXECUTION_STATE_COMPLETED,
    EXECUTION_STATE_FAILED,
    EXECUTION_STATE_INPROGRESS,
)
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

from TIPCommon.extraction import extract_configuration_param, extract_action_param
from intezer.core import constants
from intezer.core.IntezerManager import IntezerManager
from intezer.core.exceptions import IntezerManagerError


def start_operation(
    siemplify: SiemplifyAction,
    manager: IntezerManager,
    alert_id: str,
    wait_for_completion: bool = False,
) -> Tuple[str, Any, int]:
    """To start the operation for an analysis.

    Args:
        siemplify: SiemplifyAction object.
        manager: IntezerManager object.
        alert_id: The alert ID of an alert.
        wait_for_completion: Whether to wait for the completion of the action
    Returns:
        output_message: Output message to be displayed on UI.
        result_value: Result of the action.
        status: Execution state of the action.
    """
    output_message = ""
    result_value = {}
    status = EXECUTION_STATE_INPROGRESS
    try:
        response = manager.get_alert(alert_id=alert_id)
        result_key = constants.STATUS_MAP.get(response.status)
        if result_key:
            result_value[result_key] = alert_id
        if not wait_for_completion:
            output_message = (
                "Successfully fetched the alert details for the following alert id: "
                f"{alert_id} in {constants.INTEGRATION_NAME}\n"
            )
            status = EXECUTION_STATE_COMPLETED
            siemplify.result.add_result_json(response.to_json())
            result_value = True
        else:
            if result_value.get(constants.IN_PROGRESS_STATUS) or result_value.get(
                constants.QUEUED_STATUS
            ):
                output_message = (
                    f"Waiting for results for the following alert: " f"{alert_id}"
                )
                result_value = json.dumps(result_value)
            else:
                output_message = (
                    "Successfully fetched the alert details "
                    "for the following alert id: "
                    f"{alert_id} in {constants.INTEGRATION_NAME}\n"
                )
                status = EXECUTION_STATE_COMPLETED
                siemplify.result.add_result_json(response.to_json())
                result_value = True

    except IntezerManagerError as e:
        status = EXECUTION_STATE_FAILED
        result_value = False
        output_message += (
            "Action wasn't able to fetch the alert detail "
            f"for the following alert: {alert_id}: "
            f"in {constants.INTEGRATION_NAME}\n"
        )
        siemplify.LOGGER.error(f"Get alert failed - {e}")

    return output_message, result_value, status


def query_operation_status(
    siemplify: SiemplifyAction, manager: IntezerManager, alert_id: str
) -> Tuple[str, Any, int]:
    """Query the running operation of the action.

    Args:
        siemplify: SiemplifyAction object.
        manager: IntezerManager object.
        alert_id: The alert ID of the analysis.
    Returns:
        output_message: Output message to be displayed on UI.
        result_value: Result of the action.
        status: Execution state of the action.
    """
    result_value = {}
    response = manager.get_alert(alert_id=alert_id)
    result_key = constants.STATUS_MAP.get(response.status)
    if result_key:
        result_value[result_key] = alert_id

    not_finished_alert = result_value.get(
        constants.IN_PROGRESS_STATUS, None
    ) or result_value.get(constants.QUEUED_STATUS)
    if not_finished_alert:
        status = EXECUTION_STATE_INPROGRESS
        result_value = json.dumps(result_value)
        output_message = (
            f"Waiting for results for the following alert: " f"{not_finished_alert}"
        )
    else:
        output_message, result_value, status = finish_operation(
            siemplify=siemplify, alert_id=alert_id, response=response
        )

    return output_message, result_value, status


def finish_operation(siemplify, alert_id: str, response) -> Tuple[str, Any, int]:
    """Finish the operation of an action.

    Args:
        siemplify: SiemplifyAction object.
        alert_id: The alert ID of the analysis.
        response: Data from API.
    Returns:
        output_message: Output message to be displayed on UI.
        result_value: Result of the action.
        status: Execution state of the action.
    """
    result_value = True
    status = EXECUTION_STATE_COMPLETED
    siemplify.result.add_result_json(response.to_json())
    output_message = (
        "Successfully fetched the alert details for the following alert id: "
        f"{alert_id} in {constants.INTEGRATION_NAME}\n"
    )

    return output_message, result_value, status


@output_handler
def main(first_run) -> None:
    siemplify = SiemplifyAction()
    siemplify.script_name = constants.GET_ALERT_SCRIPT_NAME
    mode = "Main" if first_run else "Get Alert"

    siemplify.LOGGER.info(f"----------------- {mode} - Param Init -----------------")

    api_root = extract_configuration_param(
        siemplify,
        provider_name=constants.INTEGRATION_NAME,
        param_name="API Root",
        default_value=constants.API_URL,
        is_mandatory=True,
        print_value=True,
    )
    api_key = extract_configuration_param(
        siemplify,
        provider_name=constants.INTEGRATION_NAME,
        param_name="API key",
        is_mandatory=True,
        print_value=False,
        remove_whitespaces=False,
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=constants.INTEGRATION_NAME,
        param_name="Verify SSL",
        is_mandatory=True,
        input_type=bool,
        print_value=True,
    )

    # Action Parameters
    alert_id = extract_action_param(
        siemplify, param_name="Alert ID", is_mandatory=True, print_value=True
    )
    wait_for_completion = extract_action_param(
        siemplify,
        param_name="Wait For Completion",
        print_value=True,
        input_type=bool,
        default_value=False,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    status = EXECUTION_STATE_INPROGRESS
    result_value = False
    output_message = ""

    try:
        manager = IntezerManager(
            api_root=api_root,
            api_key=api_key,
            verify_ssl=verify_ssl,
            siemplify_logger=siemplify.LOGGER,
        )

        if first_run:
            output_message, result_value, status = start_operation(
                siemplify,
                manager=manager,
                alert_id=alert_id,
                wait_for_completion=wait_for_completion,
            )
        elif status == EXECUTION_STATE_INPROGRESS:
            output_message, result_value, status = query_operation_status(
                siemplify=siemplify, manager=manager, alert_id=alert_id
            )

    except IntezerManagerError as e:
        output_message = (
            f"Error executing action {constants.GET_ALERT_SCRIPT_NAME}. " f"Reason: {e}"
        )
        status = EXECUTION_STATE_FAILED
        siemplify.LOGGER.error(output_message)
        result_value = False

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"Result: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    is_first_run = len(sys.argv) < 3 or sys.argv[2] == "True"
    main(is_first_run)
