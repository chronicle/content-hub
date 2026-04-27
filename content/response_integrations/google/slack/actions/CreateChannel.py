from __future__ import annotations
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from ..core.SlackManager import SlackManager, SlackManagerException, UserNotFoundException
from TIPCommon import (
    extract_configuration_param,
    extract_action_param,
    convert_comma_separated_to_list,
)
from ..core.consts import PROVIDER_NAME

SCRIPT_NAME = f"{PROVIDER_NAME} - CreateChannel"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    api_token = extract_configuration_param(
        siemplify, provider_name=PROVIDER_NAME, param_name="ApiToken", input_type=str
    )

    channel_name = extract_action_param(
        siemplify,
        param_name="Channel Name",
        is_mandatory=True,
        print_value=True,
        input_type=str,
    )

    user_ids = extract_action_param(
        siemplify,
        param_name="User IDs",
        is_mandatory=False,
        print_value=True,
        input_type=str,
    )

    user_emails = extract_action_param(
        siemplify,
        param_name="User Emails",
        is_mandatory=False,
        print_value=True,
        input_type=str,
    )

    is_private = extract_action_param(
        siemplify,
        param_name="Is Private",
        is_mandatory=False,
        print_value=True,
        input_type=bool,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    result = "false"
    status = EXECUTION_STATE_COMPLETED
    json_results = []

    try:
        slack_manager = SlackManager(api_token)
        channel_info = slack_manager.create_channel(channel_name, is_private)

        if user_emails and not user_ids:
            user_ids = slack_manager.get_user_ids_by_emails(user_emails)

        if user_emails and user_ids:
            siemplify.LOGGER.info(
                "User IDs and Emails were specified, the action starting to work with IDs"
            )

        users_count = len(convert_comma_separated_to_list(user_ids))
        if user_ids:
            slack_manager.invite_to_channel(channel_info.id, user_ids)
        if is_private and not user_ids:
            output_message = f"Successfully created private channel {channel_name}."
        elif is_private and user_ids:
            output_message = f"Successfully created channel {channel_name} and added {users_count} users."
        elif not is_private and not user_ids:
            output_message = f"Successfully created channel {channel_name}."
        else:
            output_message = f"Successfully created channel {channel_name} and added {users_count} users."
        siemplify.LOGGER.info(output_message)

        json_results.append(channel_info.raw_data)
        siemplify.result.add_result_json(json_results)
        result = "true"

    except UserNotFoundException as e:
        output_message = f"Channel {channel_name} was created, but not all users were invited. Reason: {e}"
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)

    except SlackManagerException as e:
        output_message = f"Failed to create channel {channel_name}. Reason: {e}"
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)

    except Exception as e:
        output_message = f"Error executing action CreateChannel. Reason: {e}"
        status = EXECUTION_STATE_FAILED
        siemplify.LOGGER.error(f"Error executing action {SCRIPT_NAME}")
        siemplify.LOGGER.exception(e)

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"Result: {result}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.end(output_message, result, status)


if __name__ == "__main__":
    main()
