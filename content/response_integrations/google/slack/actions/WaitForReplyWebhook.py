from __future__ import annotations
from soar_sdk.ScriptResult import (
    EXECUTION_STATE_COMPLETED,
    EXECUTION_STATE_FAILED,
    EXECUTION_STATE_INPROGRESS,
)
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler, unix_now
from ..core.SlackManager import BaseURLException, SlackManager
from TIPCommon import extract_configuration_param, extract_action_param
from ..core.WebhookManager import WebhookManager
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

    webhook_base_url = extract_configuration_param(
        siemplify,
        provider_name=PROVIDER_NAME,
        param_name="WebhookBaseURL",
        input_type=str,
    )

    verify_ssl = extract_configuration_param(
        siemplify, provider_name=PROVIDER_NAME, param_name="Verify SSL", input_type=bool
    )

    webhook_token_uuid = extract_action_param(
        siemplify,
        param_name="Webhook Token UUID",
        is_mandatory=True,
        print_value=True,
        input_type=str,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    result = "false"

    try:
        slack_manager = SlackManager(api_token)
        slack_manager.test_connectivity()

        webhook_manager = WebhookManager(
            webhook_base_url, token_id=webhook_token_uuid, verify_ssl=verify_ssl
        )

        if not webhook_base_url:
            raise BaseURLException(
                f"Failed to execute action, please specify the “Webhook Base URL” "
                f"integration parameter."
            )

        replies = webhook_manager.get_data()

        is_timeout = is_async_action_global_timeout_approaching(
            siemplify, action_start_time
        )

        status = EXECUTION_STATE_COMPLETED

        if not replies and not is_timeout:
            status = EXECUTION_STATE_INPROGRESS
            result = "true"

        if replies:
            result = "true"
            output_message = f"Successfully fetched the user’s response to a webhook! Response content: {replies}"
            if status == EXECUTION_STATE_COMPLETED:
                first_reply = replies[0]
                siemplify.result.add_result_json(first_reply)
        else:
            webhook_url = f"{webhook_base_url}/{webhook_token_uuid}"
            output_message = (
                f"Waiting for the response to the sent message with a webhook. "
                f"Webhook url with uuid: {webhook_url}"
            )

        if is_timeout and not replies:
            output_message = f"A user response to a webhook was not found and the action stopped due to the timeout."

        siemplify.LOGGER.info(f"Script Name: {SCRIPT_NAME} | {output_message}")

    except BaseURLException as e:
        status = EXECUTION_STATE_FAILED
        output_message = f"{e}"
        siemplify.LOGGER.error(output_message)

    except Exception as e:
        output_message = (
            f'Failed to execute "Wait for Reply with Webhook" action! Error is {e}'
        )
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
