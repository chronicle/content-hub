from __future__ import annotations

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import convert_dict_to_json_result_dict, output_handler
from TIPCommon.extraction import extract_action_param, extract_configuration_param
from TIPCommon.transformation import construct_csv

from ..core.constants import (
    DEFAULT_MAX_DAYS_TO_RETURN,
    DEFAULT_MAX_RECORDS_TO_RETURN,
    INTEGRATION_NAME,
    LIST_RECORDS_RELATED_TO_USER_SCRIPT_NAME,
)
from ..core.exceptions import ServiceNowTableNotFoundException
from ..core.ServiceNowManager import DEFAULT_TABLE, ServiceNowManager


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = LIST_RECORDS_RELATED_TO_USER_SCRIPT_NAME

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
    usernames_str = extract_action_param(
        siemplify, param_name="Usernames", is_mandatory=True, print_value=True
    )
    max_days_backward = extract_action_param(
        siemplify,
        param_name="Max Days Backwards",
        is_mandatory=True,
        print_value=True,
        input_type=int,
        default_value=DEFAULT_MAX_DAYS_TO_RETURN,
    )
    max_records = extract_action_param(
        siemplify,
        param_name="Max Records To Return",
        is_mandatory=False,
        print_value=True,
        input_type=int,
        default_value=DEFAULT_MAX_RECORDS_TO_RETURN,
    )

    usernames = [sys_id.lower().strip() for sys_id in usernames_str.split(",") if sys_id]

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    output_message = ""
    result_value = True
    status = EXECUTION_STATE_COMPLETED
    successful_usernames, failed_usernames = [], []
    csv_name = "{}: Related {} Records"
    json_results = {}

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

        users = manager.get_user_data(usernames) if usernames else []

        validated_usernames = {user.username for user in users}
        validated_user_emails = {user.email for user in users}
        validated_users = validated_usernames.union(validated_user_emails)

        failed_usernames = [item for item in usernames if item not in validated_users]

        for user in users:
            try:
                related_data = manager.get_user_related_data(
                    user_id=user.sys_id,
                    max_records=max_records,
                    max_days_backward=max_days_backward,
                    table_name=table_name,
                )
                # Create table for each users data
                if related_data:
                    csv_table_name = csv_name.format(user.username, table_name.capitalize())
                    siemplify.result.add_data_table(
                        title=csv_table_name,
                        data_table=construct_csv([item.to_table() for item in related_data]),
                    )

                    json_results[user.username] = [item.to_json() for item in related_data]
                    successful_usernames.append(user.username)
                else:
                    failed_usernames.append(user.username)
            except ServiceNowTableNotFoundException as err:
                raise ServiceNowTableNotFoundException(err)
            except Exception as err:
                failed_usernames.append(user.username)
                siemplify.LOGGER.error(
                    "\nAction wasn't able to retrieve related records from table {} in ServiceNow "
                    "for the following user: {}".format(table_name, user.username)
                )
                siemplify.LOGGER.exception(err)

        if successful_usernames:
            output_message += (
                "Successfully retrieved related records from table {} in ServiceNow "
                "for the following users: {}".format(table_name, ", ".join(successful_usernames))
            )

        if failed_usernames:
            output_message += (
                "\nAction wasn't able to retrieve related records from table {} in ServiceNow "
                "for the following users: {}".format(table_name, ", ".join(failed_usernames))
            )

        if not successful_usernames:
            output_message = "No related table records were retrieved for the provided users."
            result_value = False

        # Add json result
        if json_results:
            siemplify.result.add_result_json(convert_dict_to_json_result_dict(json_results))
    except ServiceNowTableNotFoundException as err:
        output_message = str(err)
        result_value = False
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(err)

    except Exception as err:
        output_message = (
            f"Error executing action '{LIST_RECORDS_RELATED_TO_USER_SCRIPT_NAME}'. Reason: {err}"
        )
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
