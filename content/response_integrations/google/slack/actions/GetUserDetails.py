from __future__ import annotations
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from ..core.SlackManager import SlackManager, SlackManagerException, UserNotFoundException
from TIPCommon import extract_configuration_param, extract_action_param, construct_csv
from ..core.consts import PROVIDER_NAME

SCRIPT_NAME = f"{PROVIDER_NAME} - GetUserDetails"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    api_token = extract_configuration_param(
        siemplify, provider_name=PROVIDER_NAME, param_name="ApiToken", input_type=str
    )

    search_by = extract_action_param(
        siemplify,
        param_name="Search By",
        default_value="Email",
        is_mandatory=True,
        print_value=True,
        input_type=str,
    )

    user_value = extract_action_param(
        siemplify,
        param_name="User Value",
        is_mandatory=True,
        print_value=True,
        input_type=str,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    json_result = {}
    result = "false"
    status = EXECUTION_STATE_COMPLETED
    output_message = (
        f"Failed to find user details based on the provided criteria: \n"
        f"Search by: {search_by}\n"
        f"User value: {user_value}"
    )

    try:
        slack_manager = SlackManager(api_token)
        # Search by Email
        if search_by == "Email":
            user = slack_manager.get_user_details_by_email(user_value)
            user_id = user.id
            user = slack_manager.get_user_details_by_id(user_id)
            json_result = user.raw_data
            users_table = [user.to_csv_detailed()]
            output_message = f"User details were fetched successfully."
            result = "true"
        # Search by Name
        elif search_by == "Real Name":
            all_users = slack_manager.list_users()
            users = slack_manager.filter_users_by_real_name(all_users, user_value)
            users_table = [user.to_csv_detailed() for user in users]
            users_count = len(users)
            if users_count == 1:
                user_id = users[0].id
                user = slack_manager.get_user_details_by_id(user_id)
                json_result = user.raw_data
                output_message = f"User details were fetched successfully."
                result = "true"
            if users_count > 1:
                json_result = [user.raw_data for user in users]
                output_message = (
                    f"For the provided search criteria multiple matches were found: \n"
                    f"Search by: {search_by}\n"
                    f"User value: {user_value}"
                )
                result = "true"
        # Search by User ID
        else:
            user = slack_manager.get_user_details_by_id(user_value)
            json_result = user.raw_data
            users_table = [user.to_csv_detailed()]
            output_message = f"User details were fetched successfully."
            result = "true"

        siemplify.LOGGER.info(output_message)
        siemplify.result.add_result_json(json_result)
        for i, user_table in enumerate(users_table):
            siemplify.result.add_data_table(
                title=f"Slack User Details {i + 1}",
                data_table=construct_csv([user_table]),
            )
    except UserNotFoundException as _:
        pass
    except (SlackManagerException, Exception) as e:
        status = EXECUTION_STATE_FAILED
        output_message = f"Failed to execute “Get User Details” action! Error is {e}"
        siemplify.LOGGER.error(f"Script Name: {SCRIPT_NAME} | {output_message}")
        siemplify.LOGGER.exception(e)

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"Result: {result}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")

    siemplify.end(output_message, result, status)


if __name__ == "__main__":
    main()
