from __future__ import annotations
from soar_sdk.ScriptResult import EXECUTION_STATE_FAILED, EXECUTION_STATE_COMPLETED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

from TIPCommon.extraction import extract_action_param
from TIPCommon.transformation import construct_csv, convert_comma_separated_to_list

from g_suite.core.action_init import create_api_client
from g_suite.core.consts import INTEGRATION_NAME, LIST_USERS_SCRIPT_NAME, DEFAULT_MAX_USERS_TO_RETURN


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = f"{INTEGRATION_NAME} - {LIST_USERS_SCRIPT_NAME}"
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    # Action configuration
    customer_id = extract_action_param(
        siemplify, param_name="Customer ID", is_mandatory=False, print_value=True
    )
    domain = extract_action_param(
        siemplify, param_name="Domain", is_mandatory=False, print_value=True
    )
    manager_email = extract_action_param(
        siemplify, param_name="Manager Email", is_mandatory=False, print_value=True
    )
    only_admin_accounts = extract_action_param(
        siemplify,
        param_name="Return only Admin Accounts?",
        is_mandatory=False,
        input_type=bool,
        default_value=False,
        print_value=True,
    )
    only_delegated_admin_accounts = extract_action_param(
        siemplify,
        param_name="Return only Delegated Admin Accounts?",
        is_mandatory=False,
        input_type=bool,
        default_value=False,
        print_value=True,
    )
    only_suspended_accounts = extract_action_param(
        siemplify,
        param_name="Return only Suspended Users?",
        is_mandatory=False,
        input_type=bool,
        default_value=False,
        print_value=True,
    )
    org_unit_path = extract_action_param(
        siemplify, param_name="Org Unit Path", is_mandatory=False, print_value=True
    )
    department = extract_action_param(
        siemplify, param_name="Department", is_mandatory=False, print_value=True
    )
    max_results = extract_action_param(
        siemplify,
        param_name="Record Limit",
        is_mandatory=False,
        input_type=int,
        default_value=DEFAULT_MAX_USERS_TO_RETURN,
        print_value=True,
    )
    custom_query = extract_action_param(
        siemplify,
        param_name="Custom Query Parameter",
        is_mandatory=False,
        print_value=True,
    )

    only_without_2fa = extract_action_param(
        siemplify,
        param_name="Return only users without 2fa?",
        is_mandatory=False,
        input_type=bool,
        default_value=False,
        print_value=True,
    )
    email_addresses = convert_comma_separated_to_list(
        extract_action_param(
            siemplify,
            param_name="Email Addresses",
            is_mandatory=False,
            default_value=False,
            print_value=True,
        )
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    status = EXECUTION_STATE_FAILED
    result_value = False

    try:
        gsuite_manager = create_api_client(siemplify)
        try:
            email_addresses = [email for email in email_addresses if email]
            users = gsuite_manager.list_users(
                customer_id=customer_id,
                limit=max_results,
                domain=domain,
                manager_email=manager_email,
                only_admin_accounts=only_admin_accounts,
                only_delegated_admin_accounts=only_delegated_admin_accounts,
                only_suspended_users=only_suspended_accounts,
                org_unit_path=org_unit_path,
                department=department,
                custom_query=custom_query,
                only_without_2fa=only_without_2fa,
                email_addresses=email_addresses,
            )
            if users:
                siemplify.result.add_result_json([user.as_json() for user in users])
                siemplify.result.add_data_table(
                    "Google Gsuite Users",
                    construct_csv([user.as_csv() for user in users]),
                )
                output_message = (
                    f"Action successfully returned {INTEGRATION_NAME}"
                    "Directory user list"
                )
                result_value = True
            else:
                output_message = "No users were returned."
            status = EXECUTION_STATE_COMPLETED

        except Exception as error:
            output_message = (
                f"Error executing action {LIST_USERS_SCRIPT_NAME}. Reason: {error}"
            )
            siemplify.LOGGER.error(output_message)
            siemplify.LOGGER.exception(error)

    except Exception as error:
        output_message = (
            f"Failed to connect to Google {INTEGRATION_NAME}! Error is: {error}"
        )
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(error)

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"Result Value: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
