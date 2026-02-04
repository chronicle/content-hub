from __future__ import annotations

import sys
from datetime import datetime, timezone
from enum import Enum

from soar_sdk.ScriptResult import (
    EXECUTION_STATE_COMPLETED,
    EXECUTION_STATE_FAILED,
    EXECUTION_STATE_INPROGRESS,
)
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler, unix_now
from TIPCommon.extraction import extract_action_param, extract_configuration_param

from ..core.constants import (
    DATETIME_FORMAT,
    INTEGRATION_NAME,
    RECORD_COMMENT_TYPE_NAMES,
    WAIT_FOR_COMMENTS_SCRIPT_NAME,
)
from ..core.exceptions import ServiceNowException, ServiceNowRecordNotFoundException
from ..core.ServiceNowManager import DEFAULT_TABLE, ServiceNowManager
from ..core.UtilsManager import is_async_action_global_timeout_approaching


class WaitMode(Enum):
    UNTIL_FIRST_MESSAGE = "Until First Message"
    UNTIL_SPECIFIC_TEXT = "Until Specific Text"
    UNTIL_TIMEOUT = "Until Timeout"


def wait_for_comments(
    siemplify,
    action_start_time,
    manager,
    table_name,
    object_type,
    record_sys_id,
    text,
    wait_mode,
    time_filter,
):
    json_result = {}
    result_value = True
    status = EXECUTION_STATE_INPROGRESS
    output_message = "Waiting for messages..."

    # check if timeout approaching
    is_timeout = is_async_action_global_timeout_approaching(siemplify, action_start_time)

    # get record comments
    try:
        comments = manager.get_record_comments(table_name, object_type, record_sys_id)
        comments = filter_new_comments(comments, time_filter)
    except ServiceNowRecordNotFoundException:
        comments = []

    if is_timeout and wait_mode == WaitMode.UNTIL_TIMEOUT:
        if comments:
            json_result = [comment.to_json() for comment in comments]

        else:
            result_value = True
            status = EXECUTION_STATE_COMPLETED
            output_message = (
                f"No new {RECORD_COMMENT_TYPE_NAMES.get(object_type)} were added during the timeframe "
                f"of action execution to {table_name} with Sys ID {record_sys_id} in {INTEGRATION_NAME}."
            )

    elif is_timeout:
        status = EXECUTION_STATE_FAILED
        result_value = False
        output_message = (
            f'Error executing action "{WAIT_FOR_COMMENTS_SCRIPT_NAME}". Reason: action ran into a '
            f"timeout during execution. Please increase the timeout in IDE."
        )

    elif comments:
        if wait_mode == WaitMode.UNTIL_FIRST_MESSAGE:
            json_result = [comment.to_json() for comment in comments]

        if wait_mode == WaitMode.UNTIL_SPECIFIC_TEXT:
            comments_with_specific_text = [comment for comment in comments if comment.value == text]

            if comments_with_specific_text:
                json_result = [comment.to_json() for comment in comments_with_specific_text]

    if json_result:
        siemplify.result.add_result_json(json_result)
        status = EXECUTION_STATE_COMPLETED
        output_message = (
            f"Successfully returned {RECORD_COMMENT_TYPE_NAMES.get(object_type)} related to "
            f"{table_name} with Sys ID {record_sys_id} in {INTEGRATION_NAME}."
        )

    if status == EXECUTION_STATE_INPROGRESS:
        result_value = time_filter

    return status, result_value, output_message


@output_handler
def main(is_first_run):
    siemplify = SiemplifyAction()
    action_start_time = unix_now()
    siemplify.script_name = WAIT_FOR_COMMENTS_SCRIPT_NAME
    mode = "Main" if is_first_run else "Waiting for messages..."

    siemplify.LOGGER.info(f"----------------- {mode} - Param Init -----------------")

    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Api Root",
        print_value=True,
    )
    username = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Username",
        print_value=False,
    )
    password = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Password",
        print_value=False,
    )
    default_incident_table = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Incident Table",
        print_value=True,
        default_value=DEFAULT_TABLE,
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        default_value=True,
        input_type=bool,
    )
    client_id = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Client ID",
        print_value=False,
    )
    client_secret = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Client Secret",
        print_value=False,
    )
    refresh_token = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Refresh Token",
        print_value=False,
    )
    use_oauth = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Use Oauth Authentication",
        default_value=False,
        input_type=bool,
    )
    # Parameters
    table_name = extract_action_param(
        siemplify, param_name="Table Name", is_mandatory=True, print_value=True
    )
    record_sys_id = extract_action_param(
        siemplify, param_name="Record Sys ID", is_mandatory=True, print_value=True
    )
    object_type = extract_action_param(
        siemplify, param_name="Type", is_mandatory=True, print_value=True
    )
    wait_mode = extract_action_param(
        siemplify, param_name="Wait Mode", is_mandatory=True, print_value=True
    )
    text = extract_action_param(siemplify, param_name="Text", is_mandatory=False, print_value=True)

    additional_data = int(
        extract_action_param(siemplify=siemplify, param_name="additional_data", default_value="0")
    )

    siemplify.LOGGER.info(f"----------------- {mode} - Started -----------------")

    try:
        wait_mode = WaitMode(wait_mode)

        if wait_mode == WaitMode.UNTIL_SPECIFIC_TEXT and not text:
            raise ServiceNowException(
                '"Text" parameter is mandatory, if "Until Specific Text" is provided.'
            )

        time_filter = action_start_time if is_first_run else additional_data

        service_now_manager = ServiceNowManager(
            api_root=api_root,
            username=username,
            password=password,
            default_incident_table=default_incident_table,
            verify_ssl=verify_ssl,
            siemplify_logger=siemplify.LOGGER,
            client_id=client_id,
            client_secret=client_secret,
            refresh_token=refresh_token,
            use_oauth=use_oauth,
        )
        if is_first_run:
            _ = service_now_manager.get_record_details(
                ticket_sys_id=record_sys_id, fields=["sys_id"], table_name=table_name
            )

        status, result_value, output_message = wait_for_comments(
            siemplify,
            action_start_time,
            service_now_manager,
            table_name,
            object_type,
            record_sys_id,
            text,
            wait_mode,
            time_filter,
        )

    except Exception as e:
        output_message = f'Error executing action "{WAIT_FOR_COMMENTS_SCRIPT_NAME}". Reason: {e}'
        result_value = False
        status = EXECUTION_STATE_FAILED
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)

    siemplify.LOGGER.info(f"----------------- {mode} - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"Result Value: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")

    siemplify.end(output_message, result_value, status)


def filter_new_comments(comments, time_filter):
    """
    Filter comments based on time
    :param comments: {[Comment]} list of Comment objects
    :param time_filter: {int} time filter
    :return: {[Comment]} filtered list of Comment objects
    """
    comments = comments[::-1]

    index = next(
        (
            i
            for i, comment in enumerate(comments)
            if datetime.strptime(comment.sys_created_on, DATETIME_FORMAT).replace(
                tzinfo=timezone.utc
            )
            >= datetime.fromtimestamp(time_filter / 1000, tz=timezone.utc)
        ),
        None,
    )

    return comments[index:] if index is not None else []


if __name__ == "__main__":
    is_first_run = len(sys.argv) < 3 or sys.argv[2] == "True"
    main(is_first_run)
