from __future__ import annotations
import datetime

from dateutil.relativedelta import relativedelta

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import (
    output_handler,
    convert_string_to_unix_time,
    convert_datetime_to_unix_time,
    unix_now,
)
from ..core.SlackManager import (
    SlackManager,
    SlackManagerException,
    MaxRecordsException,
    UserAuthException,
    ChannelNotFoundException,
    UserNotFoundException,
)
from TIPCommon import extract_configuration_param, extract_action_param
from ..core.consts import PROVIDER_NAME

SCRIPT_NAME = f"{PROVIDER_NAME} - GetChannelOrUserConversationHistory"
TIMEFRAME_MAPPING = {
    "Last Hour": {"hours": 1},
    "Last 6 Hours": {"hours": 6},
    "Last 24 Hours": {"hours": 24},
    "Last Week": {"weeks": 1},
    "Last Month": "last_month",
    "Custom": "custom",
}


class TimeException(Exception):
    """Exception when the time frame is Custom, but the start time is not passed"""

    pass


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    api_token = extract_configuration_param(
        siemplify, provider_name=PROVIDER_NAME, param_name="ApiToken", input_type=str
    )

    object_id = extract_action_param(
        siemplify,
        param_name="Channel or User ID",
        is_mandatory=True,
        print_value=True,
        input_type=str,
    )

    time_frame = extract_action_param(
        siemplify,
        param_name="Time Frame",
        is_mandatory=False,
        print_value=True,
        input_type=str,
    )

    start_time = extract_action_param(
        siemplify,
        param_name="Start Time",
        is_mandatory=False,
        print_value=True,
        input_type=str,
    )

    end_time = extract_action_param(
        siemplify,
        param_name="End Time",
        is_mandatory=False,
        print_value=True,
        input_type=str,
    )

    max_records_to_return = extract_action_param(
        siemplify,
        param_name="Max Records to Return",
        is_mandatory=False,
        print_value=True,
        input_type=int,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    result = "false"
    status = EXECUTION_STATE_FAILED
    output_message = f"Failed to find conversation for provided id {object_id}"

    try:
        slack_manager = SlackManager(api_token, siemplify=siemplify)
        slack_manager.validate_max_records(max_records_to_return)

        now = datetime.datetime.now()
        range_string = TIMEFRAME_MAPPING.get(time_frame)

        # Cases: Last Hour, Last 6 Hours, Last 24 Hours, Last Week
        if isinstance(range_string, dict):
            start_time, end_time = now - datetime.timedelta(**range_string), now

        # Case: Last Month
        if range_string == "last_month":
            start_time, end_time = now - relativedelta(months=+1), now

        # Custom case
        if range_string == "custom":
            if not start_time:
                raise TimeException(
                    f"Error executing action “Get Channel or User Conversation History”. "
                    f"Reason: “Start time was not provided for the custom Time Frame.{time_frame}"
                )
            start_time = convert_string_to_unix_time(start_time)
            end_time = convert_string_to_unix_time(end_time) if end_time else unix_now()
        else:
            start_time, end_time = convert_datetime_to_unix_time(
                start_time
            ), convert_datetime_to_unix_time(end_time)

        siemplify.LOGGER.info(
            "Try to fetch the conversations by Channel ID on the first attempt"
        )
        conversation_history = []
        try:
            conversation_history = slack_manager.get_conversations_history(
                object_id,
                max_records_to_return=max_records_to_return,
                oldest=start_time,
                latest=end_time,
            )
        except ChannelNotFoundException as _:
            pass
        if not conversation_history:
            try:
                siemplify.LOGGER.info("Try to fetch the conversations by User ID")
                users_conversations = slack_manager.get_users_conversations(
                    user=object_id
                )
            except UserNotFoundException as _:
                users_conversations = []
            if users_conversations:
                first_conversation = users_conversations[0]
                conversation_id = first_conversation.id
                siemplify.LOGGER.info(
                    "Try to fetch the conversations by Channel ID on the second attempt"
                )
                try:
                    conversation_history = slack_manager.get_conversations_history(
                        conversation_id,
                        max_records_to_return=max_records_to_return,
                        oldest=start_time,
                        latest=end_time,
                    )
                except ChannelNotFoundException as _:
                    pass
                if not conversation_history:
                    output_message = (
                        f"Conversation with id {object_id} was found, "
                        f"but no messages were found for the provided time frame."
                    )
        if conversation_history:
            output_message = "Conversation history was fetched successfully."
            result = "true"
        status = EXECUTION_STATE_COMPLETED
        siemplify.LOGGER.info(f"Script Name: {SCRIPT_NAME} | {output_message}")
        siemplify.result.add_result_json(
            [item.raw_data for item in conversation_history]
        )
    except SlackManagerException as _:
        status = EXECUTION_STATE_COMPLETED
    except TimeException as e:
        output_message = f"{e}"
    except MaxRecordsException as e:
        output_message = (
            f"Error executing action “Get Channel or User Conversation History”. "
            f"Reason: {e}"
        )
    except (UserAuthException, Exception) as e:
        output_message = (
            f'Failed to execute "Get Channel or User Conversation History": {e}'
        )
        siemplify.LOGGER.error(f"Script Name: {SCRIPT_NAME} | {output_message}")
        siemplify.LOGGER.exception(e)

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"Result: {result}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")

    siemplify.end(output_message, result, status)


if __name__ == "__main__":
    main()
