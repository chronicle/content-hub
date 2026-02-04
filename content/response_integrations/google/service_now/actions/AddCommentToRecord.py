from __future__ import annotations

import sys

from soar_sdk.ScriptResult import (
    EXECUTION_STATE_COMPLETED,
    EXECUTION_STATE_FAILED,
    EXECUTION_STATE_INPROGRESS,
)
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from TIPCommon.extraction import extract_action_param, extract_configuration_param

from ..core.constants import ADD_COMMENT_TO_RECORD_SCRIPT_NAME, INTEGRATION_NAME
from ..core.ServiceNowManager import DEFAULT_TABLE, ServiceNowManager


def add_comment(manager, table_name, type, record_id, text, wait_for_reply):
    """
    Add comment/work note to record
    :param manager {ServiceNowManager} ServiceNowManager instance
    :param table_name {str} Table name
    :param type {str} Specifies if comments or work notes should be fetched
    :param record_id {str} Record ID
    :param text {str} Content of the comment or work note
    :param wait_for_reply {bool} Specifies if reply should be fetched
    :return: {tuple} status, result_value, output_message
    """
    manager.add_comment_to_record(table_name, type, record_id, text)
    result_value = True

    if wait_for_reply:
        status = EXECUTION_STATE_INPROGRESS
        output_message = "Waiting for a reply..."
    else:
        status = EXECUTION_STATE_COMPLETED
        output_message = (
            f'Successfully added comment/work note "{text}" to {table_name} with Sys ID {record_id} '
            f"in {INTEGRATION_NAME}."
        )

    return status, result_value, output_message


def get_reply(siemplify, manager, table_name, type, record_id, text):
    """
    Get comment/work note reply
    :param siemplify: SiemplifyAction object.
    :param manager {ServiceNowManager} ServiceNowManager instance
    :param table_name {str} Table name
    :param type {str} Specifies if comments or work notes should be fetched
    :param record_id {str} Record ID
    :param text {str} Content of the comment or work note
    :return: {tuple} status, result_value, output_message
    """
    results = manager.get_record_comments(table_name, type, record_id)
    comment_index = next(
        (index for (index, result) in enumerate(results) if result.value == text), None
    )
    replies = results[:comment_index]
    result_value = True

    if replies:
        first_reply = replies[-1]
        siemplify.result.add_result_json(first_reply.to_json())
        status = EXECUTION_STATE_COMPLETED
        output_message = (
            f'Successfully added comment/work note "{text}" to {table_name} with Sys ID {record_id} '
            f"in {INTEGRATION_NAME}."
        )
    else:
        status = EXECUTION_STATE_INPROGRESS
        output_message = "Waiting for a reply..."

    return status, result_value, output_message


@output_handler
def main(is_first_run):
    siemplify = SiemplifyAction()
    siemplify.script_name = ADD_COMMENT_TO_RECORD_SCRIPT_NAME
    mode = "Main" if is_first_run else "QueryState"
    siemplify.LOGGER.info(f"----------------- {mode} - Param Init -----------------")

    # Configuration.
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
    type = extract_action_param(siemplify, param_name="Type", is_mandatory=True, print_value=True)
    record_id = extract_action_param(
        siemplify, param_name="Record Sys ID", is_mandatory=True, print_value=True
    )
    text = extract_action_param(siemplify, param_name="Text", is_mandatory=True, print_value=True)
    wait_for_reply = extract_action_param(
        siemplify,
        param_name="Wait For Reply",
        is_mandatory=True,
        input_type=bool,
        print_value=True,
    )

    siemplify.LOGGER.info(f"----------------- {mode} - Started -----------------")

    try:
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
            status, result_value, output_message = add_comment(
                service_now_manager, table_name, type, record_id, text, wait_for_reply
            )
        else:
            status, result_value, output_message = get_reply(
                siemplify, service_now_manager, table_name, type, record_id, text
            )

    except Exception as e:
        siemplify.LOGGER.error(
            f"General error performing action {ADD_COMMENT_TO_RECORD_SCRIPT_NAME}"
        )
        siemplify.LOGGER.exception(e)
        result_value = False
        status = EXECUTION_STATE_FAILED
        output_message = (
            f'Error executing action "{ADD_COMMENT_TO_RECORD_SCRIPT_NAME}". Reason: {e}'
        )

    siemplify.LOGGER.info(f"----------------- {mode} - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"Result Value: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")

    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    is_first_run = len(sys.argv) < 3 or sys.argv[2] == "True"
    main(is_first_run)
