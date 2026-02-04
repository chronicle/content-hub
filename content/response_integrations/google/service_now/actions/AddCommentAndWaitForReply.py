import json
import sys

from constants import ADD_COMMENT_AND_WAIT_FOR_REPLY_SCRIPT_NAME, INTEGRATION_NAME
from dateutil import parser
from exceptions import ServiceNowNotFoundException, ServiceNowTableNotFoundException
from ScriptResult import (
    EXECUTION_STATE_COMPLETED,
    EXECUTION_STATE_FAILED,
    EXECUTION_STATE_INPROGRESS,
)
from ServiceNowManager import DEFAULT_TABLE, ServiceNowManager
from SiemplifyAction import SiemplifyAction
from SiemplifyUtils import output_handler
from TIPCommon.extraction import extract_action_param, extract_configuration_param


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = ADD_COMMENT_AND_WAIT_FOR_REPLY_SCRIPT_NAME
    siemplify.LOGGER.info("=" * 10 + " Main - Param Init " + "=" * 10)

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
    incident_number = extract_action_param(
        siemplify, param_name="Incident Number", print_value=True, is_mandatory=True
    )
    comment_to_add = extract_action_param(
        siemplify, param_name="Comment", print_value=True, is_mandatory=True
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

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

        service_now_manager.add_comment_to_incident(incident_number, comment_to_add)
        siemplify.LOGGER.info(f"Fetch {incident_number} comments")

        last_comment_creation_time = ""
        comments_list = service_now_manager.get_incident_comments(incident_number)

        for comment in comments_list:
            if comment.value == comment_to_add:
                last_comment_creation_time = comment.sys_created_on

        param_json = {incident_number: str(last_comment_creation_time)}

        output_message = f"Comment {comment_to_add} was posted at: {last_comment_creation_time}"
        result_value = json.dumps(param_json)
        status = EXECUTION_STATE_INPROGRESS
        siemplify.LOGGER.info(output_message)

    except ServiceNowNotFoundException as e:
        output_message = (
            str(e)
            if isinstance(e, ServiceNowTableNotFoundException)
            else f'Incident with number "{incident_number}" was not found'
        )
        result_value = False
        status = EXECUTION_STATE_COMPLETED
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
    except Exception as e:
        result_value = False
        status = EXECUTION_STATE_FAILED
        output_message = f"General error performing action {ADD_COMMENT_AND_WAIT_FOR_REPLY_SCRIPT_NAME}. Reason: {e}"
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)

    siemplify.end(output_message, result_value, status)


def query_job():
    siemplify = SiemplifyAction()
    siemplify.script_name = ADD_COMMENT_AND_WAIT_FOR_REPLY_SCRIPT_NAME
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

    try:
        service_now_manager = ServiceNowManager(
            api_root, username, password, default_incident_table, verify_ssl
        )

        # Extract last comment creation time and incident number
        additional_data = json.loads(siemplify.parameters["additional_data"])
        last_comment_creation_time = list(additional_data.values())[0]
        incident_number = list(additional_data.keys())[0]

        # A list of message objects with filtering
        siemplify.LOGGER.info(
            f"Search new comments in {incident_number} since {last_comment_creation_time}"
        )
        comments_list = service_now_manager.get_incident_comments(incident_number)

        new_comment_list = []
        # Check if there is new comment
        for comment in comments_list:
            if parser.parse(comment.sys_created_on) > parser.parse(last_comment_creation_time):
                new_comment_list.append(comment.value)

        new_comment = ", ".join(new_comment_list)

        if new_comment:
            siemplify.LOGGER.info(f"New comment: {new_comment}")
            output_message = f'Successfully added comment "{new_comment}" to incident with number {incident_number}.'
            status = EXECUTION_STATE_COMPLETED
            result_value = new_comment
        else:
            output_message = (
                f"Continuing...waiting for new comment to be added to {incident_number} incident"
            )
            siemplify.LOGGER.info("Not found new comment yet")
            status = EXECUTION_STATE_INPROGRESS
            result_value = siemplify.parameters["additional_data"]
    except Exception as e:
        output_message = f"General error performing action {ADD_COMMENT_AND_WAIT_FOR_REPLY_SCRIPT_NAME}. Reason: {e}"
        result_value = False
        status = EXECUTION_STATE_FAILED
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  result_value: {result_value}\n  output_message: {output_message}"
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    if len(sys.argv) < 3 or sys.argv[2] == "True":
        main()
    else:
        query_job()
