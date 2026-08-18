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

import pathlib
import abc
from typing import MutableMapping

from TIPCommon.types import SingleJson

from ...tests.common import AlreadyExistsError, IdNotFoundError

from ...core.datamodels import (
    Attachment,
    BlockSenderPolicy,
    HoldMessage,
    Message,
    MessageDetails
)
from ...core.MimecastParser import MimecastParser


class Mimecast(abc.ABC):

    def __init__(self) -> None:
        self._block_policies: MutableMapping[str, BlockSenderPolicy] = {}
        self._messages: list[Message] = []
        self._message_details: MutableMapping[str, MessageDetails] = {}
        self._attachments: list[Attachment] = []
        self._hold_messages: list[HoldMessage] = []
        self._attachment_content: MutableMapping[str, Attachment] = {}

    @property
    def block_policies(self) -> MutableMapping[str, BlockSenderPolicy]:
        return self._block_policies

    @property
    def messages(self) -> list[Message]:
        return self._messages

    @property
    def message_details(self) -> MutableMapping[str, MessageDetails]:
        return self._message_details

    @property
    def attachments(self) -> list[Attachment]:
        return self._attachments

    @property
    def hold_messages(self) -> list[HoldMessage]:
        return self._hold_messages

    @property
    def attachment_content(self) -> MutableMapping[str, Attachment]:
        return self._attachment_content

    def list_items(self, item_type: str) -> MutableMapping:
        """Lists the requested items based on the item type.

        Args:
            item_type (str): The type of items to list.
                             Options: 'block_policies'.

        Returns:
            MutableMapping: The requested mapping.

        Raises:
            ValueError: If the item_type is invalid.
        """
        item_mapping: SingleJson = {
            "block_policies": self._block_policies,
        }

        if item_type not in item_mapping:
            raise ValueError(
                f"Invalid item_type: {item_type}. Must be one of "
                f"{list(item_mapping.keys())}."
            )

        return item_mapping[item_type]

    def add_block_policy(self, raw_data: SingleJson) -> None:
        """
        Adds a block sender policy to the internal block policy registry.

        Args:
            raw_data (SingleJson): A dictionary containing raw data for
            building the `BlockSenderPolicy` object. The data must include a valid
            policy ID.

        Raises:
            AlreadyExistsError: If a policy with the given ID
            already exists in the registry.

        Returns:
            None
        """
        parser: MimecastParser = MimecastParser()
        block_policy: BlockSenderPolicy = parser.build_block_sender_policy(raw_data)

        if block_policy.policy_id in self._block_policies:
            raise AlreadyExistsError(
                f"Block Policy ID {block_policy.policy_id} already exists"
            )

        self._block_policies[block_policy.policy_id] = block_policy

    def get_block_policy(self, policy_id: str) -> BlockSenderPolicy:
        """
        Retrieves the details of a block policy by its unique identifier.
        """
        if policy_id not in self._block_policies:
            raise IdNotFoundError(f"Invalid Block Policy ID {policy_id}")
        return self._block_policies[policy_id]

    def get_first_block_policy_id(self) -> str | None:
        """
        Returns the ID of the first block policy, or None if no policies exist.
        """
        if self._block_policies:
            return list(self._block_policies.keys())[0]
        return None

    def add_message(self, message: Message) -> None:
        self._messages.append(message)

    def get_messages(self) -> list[Message]:
        return self._messages

    def add_message_details(self, message_details: MessageDetails) -> None:
        self._message_details[message_details.tracking_id] = message_details

    def get_message_details(self, message_id: str) -> MessageDetails:
        return self._message_details[message_id]

    def add_hold_message(self, hold_message: HoldMessage) -> None:
        self._hold_messages.append(hold_message)

    def get_hold_messages(self) -> list[HoldMessage]:
        return self._hold_messages

    def add_attachment(self, attachment: Attachment) -> None:
        self._attachments.append(attachment)

    def get_attachments(self) -> list[Attachment]:
        return self._attachments
