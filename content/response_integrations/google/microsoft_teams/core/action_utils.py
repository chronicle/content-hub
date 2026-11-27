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

"""Shared parameter handling and card delivery for the Adaptive Card actions."""

from __future__ import annotations

import dataclasses
from typing import TYPE_CHECKING

from TIPCommon.extraction import extract_action_param, extract_configuration_param

from .card_utils import validate_destination
from .MicrosoftConstants import (
    DEFAULT_API_ROOT,
    DEFAULT_LOGIN_API_ROOT,
    DESTINATION_CHANNEL,
    INTEGRATION_DISPLAY_NAME,
    INTEGRATION_NAME,
)
from .MicrosoftExceptions import (
    MicrosoftTeamsActionError,
    MicrosoftTeamsChannelNotFoundError,
)
from .MicrosoftManager import MicrosoftTeamsManager

if TYPE_CHECKING:
    from soar_sdk.SiemplifyAction import SiemplifyAction
    from TIPCommon.types import SingleJson

    from .datamodels import Message


@dataclasses.dataclass(frozen=True, slots=True)
class CardDestination:
    """The channel or chat that a card action targets."""

    destination_type: str
    team_name: str
    channel_name: str
    chat_id: str

    @property
    def is_channel(self) -> bool:
        """Whether the destination is a channel rather than a chat."""
        return self.destination_type == DESTINATION_CHANNEL

    def validate(self) -> None:
        """Validate the parameters required by the selected destination type."""
        validate_destination(self.destination_type, self.team_name, self.channel_name, self.chat_id)

    def __str__(self) -> str:
        """Describe the destination for output and error messages.

        Returns:
            The description, for example `channel General in team SOC`.

        """
        if self.is_channel:
            return f"channel {self.channel_name} in team {self.team_name}"
        return f"chat with ID {self.chat_id}"


def build_manager(siemplify: SiemplifyAction) -> MicrosoftTeamsManager:
    """Create a manager from the integration configuration.

    Args:
        siemplify: The action SDK object.

    Returns:
        The Microsoft Teams manager.

    """
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
    return MicrosoftTeamsManager(
        client_id=client_id,
        client_secret=secret_id,
        tenant=tenant,
        refresh_token=token,
        redirect_url=redirect_url,
        api_root=api_root,
        login_api_root=login_api_root,
        verify_ssl=verify_ssl,
    )


def extract_destination(siemplify: SiemplifyAction) -> CardDestination:
    """Read the destination parameters of a card action.

    Args:
        siemplify: The action SDK object.

    Returns:
        The destination, not yet validated.

    """
    return CardDestination(
        destination_type=extract_action_param(
            siemplify,
            param_name="Destination Type",
            default_value=DESTINATION_CHANNEL,
            print_value=True,
        ),
        team_name=extract_action_param(siemplify, param_name="Team Name", print_value=True),
        channel_name=extract_action_param(siemplify, param_name="Channel Name", print_value=True),
        chat_id=extract_action_param(siemplify, param_name="Chat ID", print_value=True),
    )


def send_card(manager: MicrosoftTeamsManager, destination: CardDestination, card: SingleJson) -> Message:
    """Send a card to a channel or a chat.

    Args:
        manager: The Microsoft Teams manager.
        destination: The channel or chat to send the card to.
        card: The Adaptive Card dictionary.

    Returns:
        The sent message.

    Raises:
        MicrosoftTeamsActionError: If the channel or chat was not found.

    """
    try:
        if destination.is_channel:
            return manager.send_card_to_channel(
                team_name=destination.team_name,
                channel_name=destination.channel_name,
                card=card,
            )
        return manager.send_card_to_chat(chat_id=destination.chat_id, card=card)
    except MicrosoftTeamsChannelNotFoundError as error:
        message = f"{destination} was not found in {INTEGRATION_DISPLAY_NAME}."
        raise MicrosoftTeamsActionError(message) from error


def update_card(
    manager: MicrosoftTeamsManager,
    destination: CardDestination,
    message_id: str,
    card: SingleJson,
) -> None:
    """Replace the card of an existing message in a channel or a chat.

    Args:
        manager: The Microsoft Teams manager.
        destination: The channel or chat containing the message.
        message_id: The ID of the message to update.
        card: The Adaptive Card dictionary.

    Raises:
        MicrosoftTeamsActionError: If the message was not found.

    """
    try:
        if destination.is_channel:
            manager.update_card_in_channel(
                team_name=destination.team_name,
                channel_name=destination.channel_name,
                message_id=message_id,
                card=card,
            )
        else:
            manager.update_card_in_chat(chat_id=destination.chat_id, message_id=message_id, card=card)
    except MicrosoftTeamsChannelNotFoundError as error:
        message = (
            f"message {message_id} in {destination} was not found or is not accessible in {INTEGRATION_DISPLAY_NAME}."
        )
        raise MicrosoftTeamsActionError(message) from error
