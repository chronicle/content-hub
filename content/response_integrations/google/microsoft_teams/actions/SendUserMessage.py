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
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyUtils import convert_dict_to_json_result_dict, output_handler, unix_now

from TIPCommon.extraction import extract_action_param, extract_configuration_param

from soar_sdk.ScriptResult import (
    EXECUTION_STATE_COMPLETED,
    EXECUTION_STATE_FAILED,
    EXECUTION_STATE_INPROGRESS,
)

from ..core.MicrosoftConstants import (
    INTEGRATION_DISPLAY_NAME,
    INTEGRATION_NAME,
    DEFAULT_TIMEOUT,
    SEND_USER_MESSAGE_ACTION,
    DEFAULT_API_ROOT,
    DEFAULT_LOGIN_API_ROOT,
)
from ..core.MicrosoftManager import MicrosoftTeamsManager
from ..core.UtilsManager import (
    is_approaching_timeout,
    is_async_action_global_timeout_approaching,
    get_first_msg_after_a_msg_id_with_different_sender_id,
    string_to_multi_value,
)


SUPPORTED_ENTITY_TYPES = [EntityTypes.USER]
ENTITY_SELECTION = "From Entities"
USER_IDENTIFIER_SELECTION = "From User Identifiers"
MESSAGE_CONTENT_TYPE = {"Text": "text", "HTML": "html"}


def start_operation(siemplify, manager, message, wait_for_reply):
    """
    Initial Function that sends a message to a channel
    :param siemplify {Obj} Siemplify object
    :param manager {Obj} Object of the MS Teams manager
    :param message {str} Message to send to the channel
    :param wait_for_reply {bool} True if we should wait for reply
    :return: {tuple} output_message, result_value, status
    """
    content_type = extract_action_param(
        siemplify, param_name="Content Type", print_value=True
    )
    user_selection = extract_action_param(
        siemplify, param_name="User Selection", print_value=True
    )
    user_identifiers = string_to_multi_value(
        extract_action_param(siemplify, param_name="User Identifiers", print_value=True)
    )
    status = EXECUTION_STATE_COMPLETED
    result_value = True
    output_message = ""
    valid_entities = []
    invalid_entities = []
    chats_to_track_list = []
    failed_chats = []
    if user_selection == ENTITY_SELECTION:
        target_entities = [
            entity.identifier
            for entity in siemplify.target_entities
            if entity.entity_type in SUPPORTED_ENTITY_TYPES
        ]
    elif user_selection == USER_IDENTIFIER_SELECTION:
        target_entities = user_identifiers
    else:
        target_entities = [
            entity.identifier
            for entity in siemplify.target_entities
            if entity.entity_type in SUPPORTED_ENTITY_TYPES
        ] + user_identifiers
    target_entities = list(set(target_entities))

    me_details = manager.check_account()

    for entity in target_entities:
        siemplify.LOGGER.info(f"Started processing entity: {entity}.")

        if (
            entity == me_details.display_name
            or entity.casefold() == me_details.email.casefold()
        ):
            invalid_entities.append(entity)
            siemplify.LOGGER.info(
                f"Finished processing entity: {entity}. The entity is the same as "
                "user used for this integration, skipping this user."
            )
        else:
            try:
                chat_id = manager.get_chat_id(entity_identifier=entity)

                if chat_id is None:
                    siemplify.LOGGER.info(
                        f"Chat with entity: {entity} doesn't exist. Creating..."
                    )
                    user_id = manager.find_user_id(user_name=entity)
                    chat_id = (
                        manager.create_chat(user_ids=[me_details.user_id, user_id])
                    ).chat_id

                message_result = manager.send_message_to_chat(
                    chat_id=chat_id,
                    message=message,
                    content_type=MESSAGE_CONTENT_TYPE.get(content_type),
                )
                valid_entities.append(entity)
                chats_to_track_list.append(
                    {
                        "user": entity,
                        "sender_id": me_details.user_id,
                        "chat_id": chat_id,
                        "message_id": message_result.message_id,
                    }
                )
                siemplify.LOGGER.info(f"Finished processing entity: {entity}.")

            except Exception as e:
                siemplify.LOGGER.error(
                    f"Processing entity: {entity}. failed. Reason {e}."
                )
                siemplify.LOGGER.exception(e)
                invalid_entities.append(entity)

    if not valid_entities:
        result_value = False
        output_message = (
            f"No messages were sent to the provided users in {INTEGRATION_DISPLAY_NAME}"
        )
    else:
        if wait_for_reply:
            status = EXECUTION_STATE_INPROGRESS
            output_message += "Successfully sent a message to the following users in {}: \n{}. \nWaiting for reply...".format(
                INTEGRATION_DISPLAY_NAME,
                "\n".join([entity for entity in valid_entities]),
            )

            for invalid_entity in invalid_entities:
                failed_chats.append(
                    {"user": invalid_entity, "chat_id": None, "message_id": None}
                )

            chats_to_track = {
                "chats_to_track": chats_to_track_list,
                "received_reply": [],
                "failed": failed_chats,
            }

            result_value = json.dumps(chats_to_track)

        else:
            output_message += (
                "Successfully sent a message to the following users in {}: \n{}".format(
                    INTEGRATION_DISPLAY_NAME,
                    "\n".join([entity for entity in valid_entities]),
                )
            )

            if invalid_entities:
                output_message += "\nAction wasn't able to send a message to the following users in {}: \n{}".format(
                    INTEGRATION_DISPLAY_NAME,
                    "\n".join([entity for entity in invalid_entities]),
                )

    return output_message, result_value, status


def query_operation_status(siemplify, manager, result_data, action_start_time):
    """
    Initial Function that sends a message to a channel
    :param siemplify {Obj} Siemplify object
    :param manager {Obj} Object of the MS Teams manager
    :param result_data {dict} Result data from the previous iteration
    :param action_start_time {int} Action start time in unix format
    :return: {tuple} output_message, result_value, status
    """
    status = EXECUTION_STATE_COMPLETED
    result_value = True
    result_data = json.loads(result_data)
    output_message = ""
    json_result = {}
    chats_to_track = result_data.get("chats_to_track")
    received_reply = result_data.get("received_reply")
    failed_chats = result_data.get("failed")

    if is_async_action_global_timeout_approaching(
        siemplify, action_start_time
    ) or is_approaching_timeout(action_start_time, DEFAULT_TIMEOUT):
        siemplify.LOGGER.info("Timeout is approaching. Action will gracefully exit")
        raise Exception(
            "messages were sent, but action ran into a timeout while waiting for a reply from the "
            "following users: \n{}. \nPlease increase the timeout in the IDE and try again. Note: if you "
            "retry action will send another message.".format(
                "\n".join([chat.get("user") for chat in chats_to_track])
            )
        )

    updated_chats_to_track = chats_to_track.copy()

    if chats_to_track:
        for chat in chats_to_track:
            message_id_original = chat.get("message_id")
            chat_id = chat.get("chat_id")
            sender_id = chat.get("sender_id")

            try:
                message_result = manager.get_chat_messages(chat_id=chat_id)
                message_result.reverse()
                first_reply = get_first_msg_after_a_msg_id_with_different_sender_id(
                    message_id=message_id_original,
                    sender_id=sender_id,
                    messages=message_result,
                )

                if first_reply:
                    chat["message_result"] = first_reply.to_json()
                    received_reply.append(chat)
                    if chat in updated_chats_to_track:
                        updated_chats_to_track.remove(chat)

            except Exception as e:
                siemplify.LOGGER.error(
                    f"Error occurred when waiting for reply in chat {chat_id}. "
                    f"Reason:{e}"
                )
                failed_chats.append(chat)
                if chat in updated_chats_to_track:
                    updated_chats_to_track.remove(chat)

    if updated_chats_to_track:
        result_data = {
            "chats_to_track": updated_chats_to_track,
            "received_reply": received_reply,
            "failed": failed_chats,
        }

        result_value = json.dumps(result_data)
        status = EXECUTION_STATE_INPROGRESS
        output_message += "Waiting for a reply from the following users: \n{}".format(
            "\n".join([chat.get("user") for chat in updated_chats_to_track])
        )
    else:
        if not received_reply:
            result_value = False
            output_message = f"No messages were sent to the provided users in {INTEGRATION_DISPLAY_NAME}"
        else:
            for reply in received_reply:
                json_result[reply.get("user")] = reply.get("message_result")

            siemplify.result.add_result_json(
                convert_dict_to_json_result_dict(json_result)
            )
            output_message += "Successfully sent a message and received replies to the following users in {}: \n{}".format(
                INTEGRATION_DISPLAY_NAME,
                "\n".join([chat.get("user") for chat in received_reply]),
            )

            if failed_chats:
                output_message += "\nAction wasn't able to send a message to the following users in {}: \n{}".format(
                    INTEGRATION_DISPLAY_NAME,
                    "\n".join([chat.get("user") for chat in failed_chats]),
                )

    return output_message, result_value, status


@output_handler
def main(is_first_run):
    siemplify = SiemplifyAction()
    action_start_time = unix_now()
    siemplify.script_name = SEND_USER_MESSAGE_ACTION
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

    message = extract_action_param(
        siemplify, param_name="Text", print_value=True, is_mandatory=True
    )
    wait_for_reply = extract_action_param(
        siemplify,
        param_name="Wait For Reply",
        print_value=True,
        is_mandatory=True,
        input_type=bool,
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
                siemplify,
                manager=manager,
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
                action_start_time=action_start_time,
                result_data=result_data,
            )

    except Exception as err:
        output_message = (
            f"Error executing action {SEND_USER_MESSAGE_ACTION}. Reason: {err}"
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
