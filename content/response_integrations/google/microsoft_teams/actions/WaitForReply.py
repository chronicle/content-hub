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

import codecs
import datetime
import json
import sys

from soar_sdk.ScriptResult import (
    EXECUTION_STATE_COMPLETED,
    EXECUTION_STATE_FAILED,
    EXECUTION_STATE_INPROGRESS,
    EXECUTION_STATE_TIMEDOUT,
)
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import convert_unixtime_to_datetime, output_handler, unix_now

from TIPCommon.extraction import extract_action_param, extract_configuration_param

from ..core.MicrosoftConstants import (
    ASYNC_MESSAGE,
    CHECK_FIRST_REPLY,
    INTEGRATION_NAME,
    REPLIES_EXP_REPLY_MESSAGE,
    REPLIES_WO_EXP_REPLY_MESSAGE,
    TIMEOUT_BUFFER_IN_SECONDS,
    TIMEOUT_MESSAGE,
    TIMEOUT_MESSAGE_NO_REPLY,
    WAIT_REPLY_SCRIPT,
    WAIT_TILL_TIMEOUT,
    DEFAULT_API_ROOT,
    DEFAULT_LOGIN_API_ROOT,
)
from ..core.MicrosoftExceptions import (
    MicrosoftTeamsChannelNotFoundError,
    MicrosoftTeamsMessageNotFoundError,
    MicrosoftTeamsTeamNotFoundError,
)
from ..core.MicrosoftManager import MicrosoftTeamsManager
from ..core.UtilsManager import get_content_values


def check_expected_reply(
    siemplify: SiemplifyAction,
    wait_method: str,
    expected_reply: str,
    result_data: str,
    is_timeout: bool | False = False,
) -> tuple[str, bool, int]:
    """Check expected reply exist in message replies and update the status.

    Args:
        siemplify (SiemplifyAction): SiemplifyAction object.
        wait_method (str): Action parameter "Wait Method" value.
        expected_reply (str): Action parameter "Expected Reply" value.
        result_data (str): json data string.
        is_timeout (bool, optional): Boolean. Defaults to False.

    Returns:
        tuple: output_message, result, status
    """
    escaped_expected_reply = codecs.decode(
        expected_reply if expected_reply is not None else "", "unicode_escape"
    )
    if is_timeout:
        output_message = TIMEOUT_MESSAGE
        result = False
        status = EXECUTION_STATE_TIMEDOUT
    else:
        result = result_data
        status = EXECUTION_STATE_INPROGRESS
        output_message = ASYNC_MESSAGE
    replies = json.loads(result_data).get("result")

    if wait_method == CHECK_FIRST_REPLY:
        if replies:
            first_reply_json = replies[-1]
            possible_content_values = get_content_values(first_reply_json)
            if (
                expected_reply is None
                or expected_reply in possible_content_values
                or escaped_expected_reply in possible_content_values
            ):
                message = (
                    REPLIES_EXP_REPLY_MESSAGE
                    if expected_reply
                    else REPLIES_WO_EXP_REPLY_MESSAGE
                )
                output_message = message
                result = True
                status = (
                    EXECUTION_STATE_COMPLETED
                    if not is_timeout
                    else EXECUTION_STATE_TIMEDOUT
                )
                json_result = {"messages": [first_reply_json]}
                siemplify.result.add_result_json(json_data=json_result)

            else:
                output_message = TIMEOUT_MESSAGE
                result = False
                status = EXECUTION_STATE_COMPLETED

    elif wait_method == WAIT_TILL_TIMEOUT:
        match_reply = False
        if expected_reply and replies:
            for reply in replies:
                possible_content_values = get_content_values(reply)
                if (
                    expected_reply in possible_content_values
                    or escaped_expected_reply in possible_content_values
                ):
                    output_message = REPLIES_EXP_REPLY_MESSAGE
                    json_result = {"messages": [reply]}
                    siemplify.result.add_result_json(json_data=json_result)
                    result = True
                    status = (
                        EXECUTION_STATE_COMPLETED
                        if not is_timeout
                        else EXECUTION_STATE_TIMEDOUT
                    )
                    match_reply = True
            if is_timeout and not match_reply:
                output_message = TIMEOUT_MESSAGE

    return (output_message, result, status)


@output_handler
def main(is_first_run=False):
    siemplify = SiemplifyAction()
    siemplify.script_name = WAIT_REPLY_SCRIPT
    script_end_time = siemplify.execution_deadline_unix_time_ms
    start_time = unix_now()

    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

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

    team_name = extract_action_param(
        siemplify, param_name="Team Name", print_value=True, is_mandatory=True
    )

    channel_name = extract_action_param(
        siemplify, param_name="Channel Name", print_value=True, is_mandatory=True
    )

    message_id = extract_action_param(
        siemplify, param_name="Message ID", print_value=True, is_mandatory=True
    )

    expected_reply = extract_action_param(
        siemplify, param_name="Expected Reply", print_value=True, is_mandatory=False
    )

    wait_method = extract_action_param(
        siemplify, param_name="Wait Method", print_value=True, is_mandatory=False
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
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
            team_id = manager.get_team_id(team_name)
            try:
                channel_id = manager.get_channel_id(team_id, channel_name)
            except MicrosoftTeamsTeamNotFoundError as error:
                raise MicrosoftTeamsChannelNotFoundError(f"{error}") from error
        else:
            result_data_json = extract_action_param(
                siemplify=siemplify,
                param_name="additional_data",
                default_value="{}",
                is_mandatory=True,
            )
            result_data = json.loads(result_data_json)
            team_id = result_data.get("team_id")
            channel_id = result_data.get("channel_id")
        replies = manager.get_message_replies(
            team_id=team_id, channel_id=channel_id, message_id=message_id
        )
        siemplify.LOGGER.info(f"Found replies: {len(replies)}")

        result_data = json.dumps(
            dict(team_id=team_id, channel_id=channel_id, result=replies)
        )

        is_timeout = is_async_action_global_timeout_approaching(
            script_end_time, start_time
        )
        if is_timeout:
            timeout_datetime = convert_unixtime_to_datetime(script_end_time)
            timeout_time = timeout_datetime - datetime.timedelta(
                seconds=TIMEOUT_BUFFER_IN_SECONDS
            )
            siemplify.LOGGER.info(
                f"Action will work till the timeout {timeout_time}. "
                f"Buffer time is {TIMEOUT_BUFFER_IN_SECONDS} seconds."
            )

            if expected_reply is None and replies:
                message = REPLIES_WO_EXP_REPLY_MESSAGE
                json_result = {
                    "messages": (
                        replies if wait_method == WAIT_TILL_TIMEOUT else [replies[-1]]
                    )
                }
                siemplify.result.add_result_json(json_data=json_result)
                result = True
                status = EXECUTION_STATE_COMPLETED
            elif expected_reply is None and not replies:
                message = TIMEOUT_MESSAGE_NO_REPLY
                result = False
                status = EXECUTION_STATE_FAILED
            else:
                message, result, status = check_expected_reply(
                    siemplify=siemplify,
                    wait_method=wait_method,
                    expected_reply=expected_reply,
                    result_data=result_data,
                    is_timeout=True,
                )

        else:
            message, result, status = check_expected_reply(
                siemplify=siemplify,
                wait_method=wait_method,
                expected_reply=expected_reply,
                result_data=result_data,
            )

        output_message = message.format(
            message_id=message_id,
            channel_name=channel_name,
            team_name=team_name,
            expected_reply=expected_reply,
        )
        siemplify.LOGGER.info(output_message)

    except MicrosoftTeamsTeamNotFoundError as e:
        output_message = (
            f"Error executing action {WAIT_REPLY_SCRIPT}. "
            f"Reason: Team '{team_name}' wasn't found."
        )
        result = False
        status = EXECUTION_STATE_FAILED
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)

    except MicrosoftTeamsChannelNotFoundError as e:
        output_message = (
            f"Error executing action {WAIT_REPLY_SCRIPT}. "
            f"Reason: Channel '{channel_name}' wasn't found in "
            f"team '{team_name}'."
        )
        result = False
        status = EXECUTION_STATE_FAILED
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)

    except MicrosoftTeamsMessageNotFoundError as e:
        output_message = (
            f"Error executing action {WAIT_REPLY_SCRIPT}. "
            f"Reason: Message with ID {message_id} wasn't found in "
            f"channel '{channel_name}' of team '{team_name}'."
        )
        result = False
        status = EXECUTION_STATE_FAILED
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)

    except Exception as e:
        output_message = f"Error executing action {WAIT_REPLY_SCRIPT}. " f"Reason: {e}"
        result = False
        status = EXECUTION_STATE_FAILED
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}"
        f"\n  is_success: {result}"
        f"\n  output_message: {output_message}"
    )
    siemplify.end(output_message, result, status)


def is_async_action_global_timeout_approaching(
    script_end_time: int, start_time: int
) -> bool:
    """Checking action global timeout is approaching.

    Args:
        script_end_time (int): siemplify.execution_deadline_unix_time_ms
        start_time (int): script start time.

    Returns:
        bool: Return True if delta of script_end_time and start_time is less
        than TIMEOUT_BUFFER_IN_SECONDS in ms.
    """
    return script_end_time - start_time < TIMEOUT_BUFFER_IN_SECONDS * 1000


if __name__ == "__main__":
    is_first_run = len(sys.argv) < 3 or sys.argv[2] == "True"
    main(is_first_run)
