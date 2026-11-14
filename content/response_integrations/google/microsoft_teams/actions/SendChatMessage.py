# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import annotations
import json
import sys

from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.ScriptResult import (
    EXECUTION_STATE_COMPLETED,
    EXECUTION_STATE_FAILED,
    EXECUTION_STATE_INPROGRESS,
)
from soar_sdk.SiemplifyUtils import output_handler, unix_now

from TIPCommon.extraction import extract_action_param, extract_configuration_param

from ..core.MicrosoftConstants import (
    INTEGRATION_NAME,
    SEND_CHAT_MESSAGE_ACTION,
    INTEGRATION_DISPLAY_NAME,
    DEFAULT_TIMEOUT,
    DEFAULT_API_ROOT,
    DEFAULT_LOGIN_API_ROOT,
)
from ..core.MicrosoftExceptions import MicrosoftTeamsChannelNotFoundError
from ..core.MicrosoftManager import MicrosoftTeamsManager
from ..core.UtilsManager import (
    get_first_msg_after_a_msg_id_with_different_sender_id,
    is_approaching_timeout,
    is_async_action_global_timeout_approaching,
)


def start_operation(manager, chat_id, message, wait_for_reply):
    """
    Initial Function that sends a message to a channel
    :param manager {Obj} Object of the MS Teams manager
    :param chat_id {str} Chat ID to which the message should be send
    :param message {str} Message to send to the channel
    :param wait_for_reply {bool} True if we should wait for reply
    :return: {tuple} output_message, result_value, status
    """
    message_result = manager.send_message_to_chat(
        chat_id=chat_id, message=message, content_type="text"
    )
    output_message = f"Successfully sent a message in chat with ID {chat_id} in {INTEGRATION_DISPLAY_NAME}."
    status = EXECUTION_STATE_COMPLETED
    result_value = True

    if wait_for_reply:
        status = EXECUTION_STATE_INPROGRESS
        output_message = (
            f"Successfully sent a message in chat with ID {chat_id} in {INTEGRATION_DISPLAY_NAME}. "
            f"Waiting for a reply..."
        )
        result_value = {
            "message_id": message_result.message_id,
            "created_date": message_result.created_date,
            "sender": message_result.sender,
        }
        result_value = json.dumps(result_value)

    return output_message, result_value, status


def query_operation_status(siemplify, manager, result_data, chat_id, action_start_time):
    """
    Function that checking for a reply to the sent message
    :param siemplify {Obj} Siemplify object
    :param manager {Obj} Object of the MS Teams manager
    :param result_data {dict} Result data from the previous iteration
    :param chat_id {str} Chat id to which message was sent
    :param action_start_time {int} Action start time in unix format
    :return: {tuple} output_message, result_value, status
    """
    status = EXECUTION_STATE_COMPLETED
    result_value = True
    result_data = json.loads(result_data)
    message_id_original = result_data.get("message_id")
    sender_id_original = result_data.get("sender")

    if is_async_action_global_timeout_approaching(
        siemplify, action_start_time
    ) or is_approaching_timeout(action_start_time, DEFAULT_TIMEOUT):
        siemplify.LOGGER.info("Timeout is approaching. Action will gracefully exit")
        raise Exception(
            "message was sent, but action ran into a timeout while waiting for a reply. Please increase"
            " the timeout in the IDE and try again. Note: if you retry action will send another message"
        )

    message_result = manager.get_chat_messages(chat_id=chat_id)
    message_result.reverse()
    first_reply = get_first_msg_after_a_msg_id_with_different_sender_id(
        message_id=message_id_original,
        sender_id=sender_id_original,
        messages=message_result,
    )
    if first_reply is not None:
        siemplify.result.add_result_json(first_reply.to_json())
        output_message = (
            "Successfully sent a message and received a reply in chat "
            f"with ID {chat_id} in {INTEGRATION_DISPLAY_NAME}."
        )
    else:
        status = EXECUTION_STATE_INPROGRESS
        result_value = json.dumps(result_data)
        output_message = "Waiting for a reply..."

    return output_message, result_value, status


@output_handler
def main(is_first_run):
    siemplify = SiemplifyAction()
    action_start_time = unix_now()
    siemplify.script_name = SEND_CHAT_MESSAGE_ACTION
    mode = "Main" if is_first_run else "Wait For Reply"
    siemplify.LOGGER.info(f"----------------- {mode} - Param Init -----------------")

    client_id = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Client ID",
        is_mandatory=True,
        print_value=True,
    )
    secret_id = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Secret ID",
        is_mandatory=True,
        print_value=False,
    )
    tenant = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Tenant",
        is_mandatory=True,
        print_value=True,
    )
    redirect_url = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Redirect URL",
        is_mandatory=False,
        print_value=True,
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        default_value=False,
        input_type=bool,
        print_value=True,
    )
    token = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Refresh Token",
        is_mandatory=True,
        print_value=False,
    )
    login_api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Login API Root",
        default_value=DEFAULT_LOGIN_API_ROOT,
        print_value=True,
    )
    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Root",
        default_value=DEFAULT_API_ROOT,
        print_value=True,
    )

    chat_id = extract_action_param(
        siemplify, param_name="Chat ID", print_value=True, is_mandatory=True
    )
    message = extract_action_param(
        siemplify, param_name="Text", print_value=True, is_mandatory=True
    )
    wait_for_reply = extract_action_param(
        siemplify, param_name="Wait For Reply", print_value=True, input_type=bool
    )

    siemplify.LOGGER.info(f"----------------- {mode} - Started -----------------")
    status = EXECUTION_STATE_COMPLETED
    result_value = False
    output_message = ""

    try:
        manager = MicrosoftTeamsManager(
            client_id=client_id,
            client_secret=secret_id,
            tenant=tenant,
            refresh_token=token,
            redirect_url=redirect_url,
            api_root=api_root,
            login_api_root=login_api_root,
            verify_ssl=verify_ssl,
        )

        if is_first_run:
            output_message, result_value, status = start_operation(
                manager=manager,
                chat_id=chat_id,
                message=message,
                wait_for_reply=wait_for_reply,
            )
        else:
            result_data = (
                result_value
                if result_value
                else extract_action_param(
                    siemplify, param_name="additional_data", default_value="{}"
                )
            )
            output_message, result_value, status = query_operation_status(
                siemplify=siemplify,
                manager=manager,
                result_data=result_data,
                chat_id=chat_id,
                action_start_time=action_start_time,
            )

    except MicrosoftTeamsChannelNotFoundError:
        output_message = (
            f"Error executing action {SEND_CHAT_MESSAGE_ACTION}. Reason: chat with ID {chat_id} was not "
            f"found in {INTEGRATION_DISPLAY_NAME}."
        )
        result_value = False
        status = EXECUTION_STATE_FAILED
    except Exception as err:
        output_message = (
            f"Error executing action {SEND_CHAT_MESSAGE_ACTION}. Reason: {err}"
        )
        result_value = False
        status = EXECUTION_STATE_FAILED
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(err)

    siemplify.LOGGER.info(f"----------------- {mode} - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  is_success: {result_value}\n  output_message: {output_message}"
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    is_first_run = len(sys.argv) < 3 or sys.argv[2] == "True"
    main(is_first_run)
