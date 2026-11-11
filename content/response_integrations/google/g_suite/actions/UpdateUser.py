from __future__ import annotations
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

from TIPCommon.extraction import extract_action_param
from TIPCommon.transformation import convert_comma_separated_to_list

from g_suite.core.action_init import create_api_client
from g_suite.core.exceptions import GSuiteManagerError, GSuiteNotFoundException
from g_suite.core.consts import INTEGRATION_NAME, UPDATE_USER_SCRIPT_NAME, USER_STATUS_TO_SUSPENDED


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = f"{INTEGRATION_NAME} - {UPDATE_USER_SCRIPT_NAME}"
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    # Action configuration
    given_name = extract_action_param(
        siemplify, param_name="Given Name", is_mandatory=False, print_value=True
    )
    family_name = extract_action_param(
        siemplify, param_name="Family Name", is_mandatory=False, print_value=True
    )
    password = extract_action_param(
        siemplify, param_name="Password", is_mandatory=False, print_value=False
    )
    primary_emails = convert_comma_separated_to_list(
        extract_action_param(
            siemplify, param_name="Email Address", is_mandatory=True, print_value=True
        )
    )
    phone = extract_action_param(
        siemplify, param_name="Phone", is_mandatory=False, print_value=True
    )
    gender = extract_action_param(
        siemplify, param_name="Gender", is_mandatory=False, print_value=True
    )
    department = extract_action_param(
        siemplify, param_name="Department", is_mandatory=False, print_value=True
    )
    organization = extract_action_param(
        siemplify, param_name="Organization", is_mandatory=False, print_value=True
    )
    change_password_at_next_login = extract_action_param(
        siemplify,
        param_name="Change Password At Next Login",
        input_type=bool,
        is_mandatory=True,
        default_value=False,
        print_value=True,
    )
    user_status = extract_action_param(
        siemplify, param_name="User Status", print_value=True
    )
    suspended = USER_STATUS_TO_SUSPENDED[user_status]

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    status = EXECUTION_STATE_COMPLETED
    result_value = False
    user_data = []
    updated_emails, failed_emails = [], []

    try:
        gsuite_manager = create_api_client(siemplify)
        primary_emails = [email for email in primary_emails if email]
        for email in primary_emails:
            try:
                user = gsuite_manager.update_user(
                    primary_email=email,
                    given_name=given_name,
                    family_name=family_name,
                    password=password,
                    phone=phone,
                    gender=gender,
                    department=department,
                    organization=organization,
                    change_password_at_next_login=change_password_at_next_login,
                    suspended=suspended,
                )
                user_data.append(user.as_json())
                updated_emails.append(email)
                siemplify.LOGGER.info(
                    "Successfully updated the following user in "
                    f"Google Workspace: {email}"
                )
            except (GSuiteManagerError, GSuiteNotFoundException) as error:
                failed_emails.append(email)
                siemplify.LOGGER.info(
                    f"Failed to update the following user in Google Workspace: {email}"
                )
                siemplify.LOGGER.exception(error)

        if updated_emails:
            siemplify.result.add_result_json(user_data)
            result_value = True  # At least one user updated, consider it a success
            output_message = (
                "Successfully updated the following users in "
                f"Google Workspace: {', '.join(updated_emails)}"
            )

            if failed_emails:
                output_message += (
                    "\nAction wasn't able to update the following users in Google "
                    f"Workspace: {', '.join(failed_emails)}"
                )
        else:
            output_message = "None of the provided users were updated."

    except Exception as error:
        output_message = (
            f"Error executing action {UPDATE_USER_SCRIPT_NAME}. Reason: {error}"
        )
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(error)
        status = EXECUTION_STATE_FAILED

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"Result Value: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
