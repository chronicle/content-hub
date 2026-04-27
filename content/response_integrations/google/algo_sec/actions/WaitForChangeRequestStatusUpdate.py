from __future__ import annotations
import sys
from ..core.AlgoSecManager import AlgoSecManager
from soar_sdk.ScriptResult import (
    EXECUTION_STATE_COMPLETED,
    EXECUTION_STATE_FAILED,
    EXECUTION_STATE_INPROGRESS,
)
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler, unix_now
from TIPCommon import extract_configuration_param, extract_action_param
from ..core.constants import (
    INTEGRATION_NAME,
    WAIT_FOR_CHANGE_REQUEST_STATUS_UPDATE_SCRIPT_NAME,
    DEFAULT_TIMEOUT,
    POSSIBLE_STATUSES,
)
from ..core.UtilsManager import (
    is_approaching_timeout,
    is_async_action_global_timeout_approaching,
    convert_comma_separated_to_list,
    convert_list_to_comma_string,
)


@output_handler
def main(is_first_run):
    siemplify = SiemplifyAction()
    action_start_time = unix_now()
    siemplify.script_name = WAIT_FOR_CHANGE_REQUEST_STATUS_UPDATE_SCRIPT_NAME
    mode = "Main" if is_first_run else "Wait for Change Request Status Update"
    siemplify.LOGGER.info(f"----------------- {mode} - Param Init -----------------")

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
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        input_type=bool,
        is_mandatory=True,
        print_value=True,
    )

    # Action parameters
    request_id = extract_action_param(
        siemplify, param_name="Request ID", is_mandatory=True, print_value=True
    )
    statuses = extract_action_param(
        siemplify, param_name="Status", is_mandatory=True, print_value=True
    )

    siemplify.LOGGER.info(f"----------------- {mode} - Started -----------------")

    statuses = convert_comma_separated_to_list(statuses)
    result_value = True
    status = EXECUTION_STATE_COMPLETED

    try:
        invalid_statuses = [
            status for status in statuses if status not in POSSIBLE_STATUSES
        ]
        if statuses and len(invalid_statuses) == len(statuses):
            raise Exception(
                f'Invalid values provided for "Status" parameter. Possible values are: '
                f"{convert_list_to_comma_string(POSSIBLE_STATUSES)}."
            )
        elif invalid_statuses:
            statuses = [status for status in statuses if status not in invalid_statuses]
            siemplify.LOGGER.info(
                f'Following values are invalid for "Status" parameter: '
                f"{convert_list_to_comma_string(invalid_statuses)}."
            )

        manager = AlgoSecManager(
            api_root=api_root,
            username=username,
            password=password,
            verify_ssl=verify_ssl,
            siemplify_logger=siemplify.LOGGER,
        )

        request_obj = manager.get_request_details(request_id=request_id)

        if is_async_action_global_timeout_approaching(
            siemplify, action_start_time
        ) or is_approaching_timeout(action_start_time, DEFAULT_TIMEOUT):
            siemplify.LOGGER.info("Timeout is approaching. Action will gracefully exit")
            raise Exception(
                f"action ran into a timeout during execution. Current status of the change request: "
                f"{request_obj.status}. Please increase the timeout for the action in the IDE."
            )
        else:
            if request_obj.status in statuses:
                siemplify.result.add_result_json(request_obj.to_json())
                output_message = (
                    f"Status of the change request with ID {request_id} was updated to status: "
                    f"{request_obj.status}."
                )
            else:
                output_message = f"Waiting for a change request to be updated..."
                result_value = request_obj.status
                status = EXECUTION_STATE_INPROGRESS

    except Exception as err:
        output_message = f"Error executing action {WAIT_FOR_CHANGE_REQUEST_STATUS_UPDATE_SCRIPT_NAME}. Reason: {err}"
        result_value = False
        status = EXECUTION_STATE_FAILED
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(err)

    siemplify.LOGGER.info(f"----------------- {mode} - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  is_success: {result_value}\n  output_message: {output_message}"
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    is_first_run = len(sys.argv) < 3 or sys.argv[2] == "True"
    main(is_first_run)
