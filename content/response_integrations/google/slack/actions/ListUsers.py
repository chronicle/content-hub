from __future__ import annotations
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from ..core.SlackManager import SlackManager, SlackManagerException, MaxRecordsException
from TIPCommon import extract_configuration_param, construct_csv, extract_action_param
from ..core.consts import PROVIDER_NAME

SCRIPT_NAME = f"{PROVIDER_NAME} - ListUsers"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    api_token = extract_configuration_param(
        siemplify, provider_name=PROVIDER_NAME, param_name="ApiToken", input_type=str
    )

    filter_key = extract_action_param(
        siemplify, param_name="Filter Key", is_mandatory=False, print_value=True
    )
    filter_value = extract_action_param(
        siemplify, param_name="Filter Value", is_mandatory=False, print_value=True
    )
    filter_logic = extract_action_param(
        siemplify,
        param_name="Filter Logic",
        is_mandatory=False,
        input_type=str,
        print_value=True,
    )

    max_records_to_return = extract_action_param(
        siemplify,
        param_name="Max Records to Return",
        default_value=20,
        print_value=True,
        input_type=int,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    result = "false"

    try:
        slack_manager = SlackManager(api_token)
        slack_manager.validate_max_records(max_records_to_return)
        raw_users = slack_manager.list_users()
        users = slack_manager.filter_list_items(
            raw_users,
            filter_key=filter_key,
            filter_value=filter_value,
            filter_logic=filter_logic,
            max_records_to_return=max_records_to_return,
        )
        users_count = len(users)
        output_message = (
            f"No user accounts were found for the provided criteria in Slack."
        )
        if users_count:
            output_message = f"Successfully found {users_count} user accounts for the provided criteria in Slack"
            result = "true"
        if filter_logic == "Not Specified" or not filter_value:
            output_message += "\nThe filter was not applied, because parameter “Filter Value” has an empty value"
        status = EXECUTION_STATE_COMPLETED
        siemplify.LOGGER.info(f"Script Name: {SCRIPT_NAME} | {output_message}")
        siemplify.result.add_result_json([user.raw_data for user in users])

        users_table = [user.to_csv() for user in users]
        # TODO: Remove if below after construct_csv with empty list fix
        if users_table:
            siemplify.result.add_data_table(
                title="Users", data_table=construct_csv(users_table)
            )
    except (SlackManagerException, MaxRecordsException, Exception) as e:
        output_message = f"Error executing action “List Users”. Reason: {e}"
        status = EXECUTION_STATE_FAILED
        siemplify.LOGGER.error(f"Script Name: {SCRIPT_NAME} | {output_message}")
        siemplify.LOGGER.exception(e)

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"Result: {result}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")

    siemplify.end(output_message, result, status)


if __name__ == "__main__":
    main()
