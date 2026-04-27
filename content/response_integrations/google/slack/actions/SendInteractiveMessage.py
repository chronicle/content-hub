from __future__ import annotations
import sys

from soar_sdk.ScriptResult import (
    EXECUTION_STATE_COMPLETED,
    EXECUTION_STATE_FAILED,
    EXECUTION_STATE_INPROGRESS,
)
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler, unix_now
from ..core.SlackManager import (
    SlackManager,
    SlackManagerException,
    UserNotFoundException,
    ChannelNotFoundException,
)
from TIPCommon import extract_configuration_param, extract_action_param
from ..core.WebhookManager import WebhookManager
from ..core.consts import PROVIDER_NAME, GLOBAL_TIMEOUT_THRESHOLD_IN_MIN

SCRIPT_NAME = f"{PROVIDER_NAME} - SendInteractiveMessage"


class BaseURLException(Exception):
    """Exception when base url is not specified"""

    pass


@output_handler
def main(is_initial_run):
    siemplify = SiemplifyAction()
    action_start_time = unix_now()
    siemplify.script_name = SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    api_token = extract_configuration_param(
        siemplify, provider_name=PROVIDER_NAME, param_name="ApiToken", input_type=str
    )

    webhook_base_url = extract_configuration_param(
        siemplify,
        provider_name=PROVIDER_NAME,
        param_name="WebhookBaseURL",
        input_type=str,
    )

    verify_ssl = extract_configuration_param(
        siemplify, provider_name=PROVIDER_NAME, param_name="Verify SSL", input_type=bool
    )

    message = extract_action_param(
        siemplify,
        param_name="Message",
        is_mandatory=True,
        print_value=True,
        input_type=str,
    )

    recipient = extract_action_param(
        siemplify,
        param_name="Recipient",
        is_mandatory=True,
        print_value=True,
        input_type=str,
    )

    recipient_type = extract_action_param(
        siemplify,
        param_name="Recipient Type",
        default_value="Name",
        is_mandatory=True,
        print_value=True,
        input_type=str,
    )

    webhook_token_uuid = extract_action_param(
        siemplify, param_name="Webhook Token UUID", is_mandatory=True, print_value=False
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    result = "false"

    try:
        slack_manager = SlackManager(api_token)
        webhook_manager = WebhookManager(
            webhook_base_url, token_id=webhook_token_uuid, verify_ssl=verify_ssl
        )

        if not webhook_base_url:
            raise BaseURLException(
                f"Failed to execute action, please specify the “Webhook Base URL” "
                f"integration parameter."
            )

        # Send the message only one time on first run
        if is_initial_run:
            if recipient_type == "Name":
                all_users = slack_manager.list_users()
                user = slack_manager.get_user_by_name(all_users, username=recipient)
                if user:
                    recipient = user.id
            if recipient_type == "Email":
                user = slack_manager.get_user_details_by_email(recipient)
                recipient = user.id

            slack_manager.send_message(recipient, message, "blocks")
            siemplify.LOGGER.info("Message was sent successfully")

        is_timeout = is_async_action_global_timeout_approaching(
            siemplify, action_start_time
        )

        status = EXECUTION_STATE_INPROGRESS
        if not is_timeout:
            result = "true"
            output_message = (
                f"Waiting for the response to the sent message with a webhook. "
                f"Webhook url with uuid: {webhook_base_url}/{webhook_token_uuid}"
            )
            res_json = webhook_manager.get_data()
            response_count = len(res_json)
            if response_count > 0:
                status = EXECUTION_STATE_COMPLETED
                output_message = f"Successfully fetched the user’s response to a webhook! Response content {res_json}"
                siemplify.result.add_result_json(res_json)
        else:
            status = EXECUTION_STATE_COMPLETED
            output_message = f"A user response to a webhook was not found and the action stopped due to the timeout."

    except (UserNotFoundException, ChannelNotFoundException) as _:
        status = EXECUTION_STATE_COMPLETED
        output_message = (
            f"Message was not sent as the specified recipient {recipient} "
            f"with type {recipient_type} was not found"
        )
        siemplify.LOGGER.error(output_message)

    except BaseURLException as e:
        status = EXECUTION_STATE_FAILED
        output_message = f"{e}"
        siemplify.LOGGER.error(output_message)

    except (SlackManagerException, Exception) as e:
        status = EXECUTION_STATE_FAILED
        output_message = (
            f"Failed to execute “Send Interactive Message” action! Error is: {e}"
        )
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
    is_first_run = len(sys.argv) < 3 or sys.argv[2] == "True"
    main(is_first_run)
