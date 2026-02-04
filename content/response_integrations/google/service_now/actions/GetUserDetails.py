from __future__ import annotations

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from TIPCommon.extraction import extract_action_param, extract_configuration_param
from TIPCommon.transformation import construct_csv, string_to_multi_value

from ..core.constants import (
    GET_USER_DETAILS_SCRIPT_NAME,
    INTEGRATION_NAME,
    USERS_CVS_FILE_NAME,
)
from ..core.exceptions import ServiceNowException
from ..core.ServiceNowManager import DEFAULT_TABLE, ServiceNowManager


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = GET_USER_DETAILS_SCRIPT_NAME

    siemplify.LOGGER.info("----------------- Main - Param init -----------------")
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
    user_sys_ids_str = extract_action_param(
        siemplify, param_name="User Sys IDs", print_value=True, is_mandatory=False
    )
    emails_str = extract_action_param(
        siemplify, param_name="Emails", print_value=True, is_mandatory=False
    )

    user_sys_ids = string_to_multi_value(user_sys_ids_str)
    emails = string_to_multi_value(emails_str)

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    output_message = ""
    result_value = True
    status = EXECUTION_STATE_COMPLETED
    success_ids, failed_ids = [], []

    try:
        manager = ServiceNowManager(
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

        if not (user_sys_ids or emails):
            raise ServiceNowException(
                'You need to have a value in either "User Sys IDs" or "Emails" parameter.'
            )

        users = set(manager.get_user_details(sys_ids=user_sys_ids, emails=emails))

        user_ids = {user.sys_id for user in users}
        user_emails = {user.email for user in users}

        success_ids = user_ids.intersection(user_sys_ids)
        success_emails = user_emails.intersection(emails)
        success_identifiers = success_ids.union(success_emails)

        failed_ids = set(user_sys_ids).difference(success_ids)
        failed_emails = set(emails).difference(success_emails)
        failed_identifiers = failed_ids.union(failed_emails)

        if users:
            # Add json result
            siemplify.result.add_result_json([user.to_json() for user in users])
            # Add data to csv file
            siemplify.result.add_data_table(
                title=USERS_CVS_FILE_NAME,
                data_table=construct_csv([user.to_table() for user in users]),
            )

        if success_identifiers:
            output_message = (
                "Successfully retrieved information about users from "
                "ServiceNow with the following identifiers:\n"
                f"{', '.join(success_identifiers)} \n"
            )

        if failed_identifiers:
            output_message += (
                "Action wasn't able to retrieve information about the users "
                "in Service Now with the following identifiers:\n"
                f"{', '.join(failed_identifiers)} \n"
            )

        if not success_identifiers:
            output_message = (
                "Information about the users with specified identifiers "
                "was not found in Service Now"
            )
            result_value = False

    except Exception as err:
        output_message = f"Error executing action '{GET_USER_DETAILS_SCRIPT_NAME}'. Reason: {err}"
        result_value = False
        status = EXECUTION_STATE_FAILED
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(err)

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  result_value: {result_value}\n  output_message: {output_message}"
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
