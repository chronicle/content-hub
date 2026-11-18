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

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from TIPCommon.extraction import extract_action_param, extract_configuration_param

from ..core.CardUtils import (
    format_warnings,
    parse_card,
    validate_card,
    validate_destination,
)
from ..core.MicrosoftConstants import (
    DEFAULT_API_ROOT,
    DEFAULT_LOGIN_API_ROOT,
    DESTINATION_CHANNEL,
    DESTINATION_CHAT,
    INTEGRATION_DISPLAY_NAME,
    INTEGRATION_NAME,
    UPDATE_CARD_ACTION,
)
from ..core.MicrosoftExceptions import (
    MicrosoftTeamsActionError,
    MicrosoftTeamsChannelNotFoundError,
)
from ..core.MicrosoftManager import MicrosoftTeamsManager


@output_handler
def main() -> None:
    """Replace the Adaptive Card of an existing Microsoft Teams message."""
    siemplify = SiemplifyAction()
    siemplify.script_name = UPDATE_CARD_ACTION
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    status = EXECUTION_STATE_COMPLETED
    result_value = True
    output_message = ""

    try:
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

        destination = extract_action_param(
            siemplify,
            param_name="Destination Type",
            default_value=DESTINATION_CHANNEL,
            print_value=True,
        )
        team_name = extract_action_param(siemplify, param_name="Team Name", print_value=True)
        channel_name = extract_action_param(siemplify, param_name="Channel Name", print_value=True)
        chat_id = extract_action_param(siemplify, param_name="Chat ID", print_value=True)
        message_id = extract_action_param(siemplify, param_name="Message ID", is_mandatory=True, print_value=True)
        raw_card = extract_action_param(siemplify, param_name="Card JSON", is_mandatory=True, print_value=False)

        siemplify.LOGGER.info("----------------- Main - Started -----------------")
        validate_destination(destination, team_name, channel_name, chat_id)
        warnings: list[str] = []
        card = parse_card(raw_card, warnings)
        warnings.extend(validate_card(card))
        for warning in warnings:
            siemplify.LOGGER.warn(warning)

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

        try:
            if destination == DESTINATION_CHANNEL:
                manager.update_card_in_channel(
                    team_name=team_name,
                    channel_name=channel_name,
                    message_id=message_id,
                    card=card,
                )
                output_message = (
                    f"Successfully updated the card of message {message_id} in "
                    f"channel {channel_name} in team {team_name} in "
                    f"{INTEGRATION_DISPLAY_NAME}."
                )
            else:
                manager.update_card_in_chat(chat_id=chat_id, message_id=message_id, card=card)
                output_message = (
                    f"Successfully updated the card of message {message_id} in "
                    f"chat with ID {chat_id} in {INTEGRATION_DISPLAY_NAME}."
                )
        except MicrosoftTeamsChannelNotFoundError as error:
            target = (
                f"chat with ID {chat_id}"
                if destination == DESTINATION_CHAT
                else f"channel {channel_name} in team {team_name}"
            )
            message = (
                f"message {message_id} in {target} was not found or is not accessible in {INTEGRATION_DISPLAY_NAME}."
            )
            raise MicrosoftTeamsActionError(message) from error

        siemplify.result.add_result_json({"id": message_id, "status": "updated"})
        output_message += format_warnings(warnings)

    except Exception as e:
        output_message = f"Error executing action {UPDATE_CARD_ACTION}. Reason: {e}"
        siemplify.LOGGER.exception(output_message)
        status = EXECUTION_STATE_FAILED
        result_value = False

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"\n  status: {status}\n  result_value: {result_value}\n  output_message: {output_message}")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
