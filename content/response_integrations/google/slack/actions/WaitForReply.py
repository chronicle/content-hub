from __future__ import annotations
from soar_sdk.ScriptResult import (
    EXECUTION_STATE_COMPLETED,
    EXECUTION_STATE_FAILED,
    EXECUTION_STATE_INPROGRESS,
)
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler, unix_now
from ..core.SlackManager import SlackManager, SlackManagerException
from TIPCommon import extract_configuration_param, extract_action_param
from ..core.consts import PROVIDER_NAME, GLOBAL_TIMEOUT_THRESHOLD_IN_MIN

SCRIPT_NAME = f"{PROVIDER_NAME} - WaitForReply"


@output_handler
def main():
    siemplify = SiemplifyAction()
    action_start_time = unix_now()
    siemplify.script_name = SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    api_token = extract_configuration_param(
        siemplify, provider_name=PROVIDER_NAME, param_name="ApiToken", input_type=str
    )

    ts = extract_action_param(
        siemplify,
        param_name="Message Timestamp",
        is_mandatory=True,
        print_value=True,
        input_type=str,
    )

    channel_name = extract_action_param(
        siemplify,
        param_name="Channel",
        is_mandatory=False,
        print_value=True,
        input_type=str,
    )

    channel_id = extract_action_param(
        siemplify,
        param_name="Channel ID",
        is_mandatory=False,
        print_value=True,
        input_type=str,
    )

    wait_multiple_replies = extract_action_param(
        siemplify,
        param_name="Wait for Multiple Replies",
        default_value=None,
        is_mandatory=False,
        print_value=True,
        input_type=bool,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    result = "false"

    try:
        slack_manager = SlackManager(api_token)

        if not (channel_name or channel_id):
            err_msg = (
                "Either Channel or Channel ID parameters must be specified. Aborting."
            )
            siemplify.LOGGER.error(err_msg)
            siemplify.end(err_msg, "false", EXECUTION_STATE_FAILED)
        if channel_id:
            if channel_name:
                siemplify.LOGGER.warn(
                    f"Both Channel and Channel ID parameters were provided. "
                    f"Only Channel ID will be used."
                )
            siemplify.LOGGER.info(f"Fetching replies for channel {channel_id}")
        else:
            siemplify.LOGGER.info(f"Fetching channel ID for channel {channel_name}")
            channel = slack_manager.get_channel_by_name(channel_name)
            siemplify.LOGGER.info(f"Fetching replies for channel {channel_id}")
            channel_id = channel.id

        replies = slack_manager.get_message_replies(channel_id, ts)

        is_timeout = is_async_action_global_timeout_approaching(
            siemplify, action_start_time
        )

        status = EXECUTION_STATE_COMPLETED

        if (wait_multiple_replies or not replies) and not is_timeout:
            status = EXECUTION_STATE_INPROGRESS
            result = "true"

        if replies:
            result = "true"
            replies_count = len(replies)
            output_message = f"A reply was found for the message in the channel."
            if replies_count > 1:
                output_message = f"{replies_count} replies were found for the message in the channel."
            if status == EXECUTION_STATE_COMPLETED:
                replies = sorted(replies, key=lambda reply: reply.ts)
                if wait_multiple_replies:
                    siemplify.result.add_result_json(
                        [reply.raw_data for reply in replies]
                    )
                else:
                    first_reply = replies[0]
                    siemplify.result.add_result_json(first_reply.raw_data)
        else:
            output_message = "No replies were found for the message in the channel."
        siemplify.LOGGER.info(f"Script Name: {SCRIPT_NAME} | {output_message}")

    except (SlackManagerException, Exception) as e:
        output_message = f"An error occurred when trying to get message replies: {e}"
        status = EXECUTION_STATE_FAILED
        siemplify.LOGGER.error(f"Script Name: {SCRIPT_NAME} | {output_message}")
        siemplify.LOGGER.exception(e)

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"Result: {result}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")

    siemplify.end(output_message, result, status)


def is_async_action_global_timeout_approaching(siemplify, start_time):
    return (
        siemplify.execution_deadline_unix_time_ms - start_time
        < GLOBAL_TIMEOUT_THRESHOLD_IN_MIN * 60 * 1000
    )


if __name__ == "__main__":
    main()
