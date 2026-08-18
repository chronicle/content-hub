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
import copy
from datetime import datetime, timezone

import pytest

from ..core.MimecastManager import (
    EmailSearchCriteria,
    MimecastManager,
)
from ..core.datamodels import (
    Attachment,
    BlockSenderPolicyActionParams,
    HoldMessage,
    Message,
    MessageDetails,
)
from ..tests.core.product import Mimecast
from ..tests.core.session import MimecastSession
from ..tests.common import (
    ATTACHMENT,
    HOLD_MESSAGE,
    MESSAGE,
    MESSAGE_DETAILS,
    MOCK_DATA
)


class TestMimecastManager:
    """Unit tests for Mimecast Integration's MimecastManager methods."""

    def test_ping_success(
        self,
        manager: MimecastManager,
        script_session: MimecastSession,
    ) -> None:
        """Test ping success.

        Verify that the test_connectivity method successfully pings the Mimecast API.

        Args:
            manager (MimecastManager): MimecastManager object.
            script_session (MimecastSession): MimecastSession object.
        """
        manager.test_connectivity()

        assert len(script_session.request_history) == 2
        assert script_session.request_history[1].response.status_code == 200

    def test_create_block_sender_policy_success(
        self,
        manager: MimecastManager,
        mimecast: Mimecast,
        script_session: MimecastSession,
    ) -> None:
        """Test creating a block sender policy successfully.

        Args:
            manager (MimecastManager): MimecastManager object.
            script_session (MimecastSession): MimecastSession object.
        """
        mimecast.add_block_policy(
            MOCK_DATA["create_block_sender_policy_success"]["data"][0]
        )
        action_params: BlockSenderPolicyActionParams = BlockSenderPolicyActionParams(
            response="Block Sender",
            description="Test Policy",
            extracted_data="From Header",
            sender="test@example.com",
            sender_type="Email Address",
            recipient="recipient@example.com",
            recipient_type="Email Address",
            comment="Test Comment",
            bidirectional=False,
            enforced=True,
            start_time="2024-01-01T00:00:00Z",
            end_time="2024-12-31T23:59:59Z",
        )
        policy: BlockSenderPolicyActionParams = manager.create_block_sender_policy(
            action_params
        )

        assert policy.policy_id == "some_id"
        assert len(script_session.request_history) == 2
        assert script_session.request_history[1].response.status_code == 200

    def test_create_block_sender_policy_failure(
        self,
        manager: MimecastManager,
        script_session: MimecastSession,
    ) -> None:
        """Test creating a block sender policy with failure.

        Args:
            manager (MimecastManager): MimecastManager object.
            script_session (MimecastSession): MimecastSession object.
        """
        action_params: BlockSenderPolicyActionParams = BlockSenderPolicyActionParams(
            response="Block Sender",
            description="Test Policy",
            extracted_data="From Header",
            sender="test@example.com",
            sender_type="Email Address",
            recipient="recipient@example.com",
            recipient_type="Email Address",
            comment="wrong_format",
            bidirectional=False,
            enforced=True,
            start_time="2024-01-01T00:00:00Z",
            end_time="2024-12-31T23:59:59Z",
        )
        with pytest.raises(Exception) as e:
            manager.create_block_sender_policy(action_params)

        assert len(script_session.request_history) == 2
        assert script_session.request_history[1].response.status_code == 200
        assert "Invalid fromValue" in str(e.value)

    def test_search_emails(
        self,
        manager: MimecastManager,
        mimecast: Mimecast,
        script_session: MimecastSession,
    ) -> None:
        # Arrange
        message_1: Message = copy.deepcopy(MESSAGE)
        message_1.tracking_id = "Test_Id_3"
        message_1.received = ("2025-04-16T16:07:14+0000",)
        message_1.raw_data["id"] = message_1.tracking_id
        message_1.raw_data["received"] = message_1.received
        message_2: Message = copy.deepcopy(MESSAGE)
        message_2.tracking_id = "Test_Id_4"
        message_2.received = ("2025-04-16T18:07:14+0000",)
        mimecast.add_message(message_1)
        mimecast.add_message(message_2)

        message_2.raw_data["id"] = message_2.tracking_id
        message_2.raw_data["received"] = message_2.received
        message_details_1: MessageDetails = copy.deepcopy(MESSAGE_DETAILS)
        message_details_1.tracking_id = "Test_Id_3"
        message_details_1.reason = "Reason1"
        message_details_1.sent = "2025-04-16T15:32:49+0000"
        message_details_1.raw_data["id"] = message_details_1.tracking_id
        message_details_1.raw_data["recipientInfo"]["messageInfo"][
            "sent"
        ] = message_details_1.sent
        message_details_1.raw_data["queueInfo"]["reason"] = message_details_1.reason
        message_details_2: MessageDetails = copy.deepcopy(MESSAGE_DETAILS)
        message_details_2.tracking_id = "Test_Id_4"
        message_details_2.reason = "OtherReason"
        message_details_2.sent = "2025-04-16T18:32:49+0000"
        message_details_2.raw_data["id"] = message_details_2.tracking_id
        message_details_2.raw_data["recipientInfo"]["messageInfo"][
            "sent"
        ] = message_details_2.sent
        message_details_2.raw_data["queueInfo"]["reason"] = message_details_2.reason
        mimecast.add_message_details(message_details_1)
        mimecast.add_message_details(message_details_2)

        # Act
        result = manager.search_emails(
            criteria=EmailSearchCriteria(
                start_timestamp=datetime(2023, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
                domains=["abc.com"],
                statuses=["held"],
                routes=["test_route"],
                queue_reason_filter=["reason1", "reason2"],
            ),
            existing_ids=["Test_Id_1", "Test_Id_2"],
            limit=20,
        )

        # Assert
        assert len(script_session.request_history) == 7
        assert script_session.request_history[0].response.status_code == 200
        assert len(result) == 2
        assert result[0].tracking_id == "Test_Id_3"
        assert result[0].message_details.reason == "Reason1"
        assert len(mimecast.messages) == 2
        assert len(mimecast.message_details) == 2

    def test_get_hold_message_details(
        self,
        manager: MimecastManager,
        mimecast: Mimecast,
        script_session: MimecastSession,
    ) -> None:
        hold_message_1: HoldMessage = copy.deepcopy(HOLD_MESSAGE)
        hold_message_1.message_id = "Test_Id_1"
        hold_message_1.subject = "TestSubject"
        hold_message_1.sender = "TestSender"
        hold_message_1.raw_data["id"] = hold_message_1.message_id
        hold_message_1.raw_data["subject"] = hold_message_1.subject
        hold_message_1.raw_data["sender"] = hold_message_1.sender
        mimecast.add_hold_message(hold_message_1)

        attachment_1: Attachment = copy.deepcopy(ATTACHMENT)
        attachment_2: Attachment = copy.deepcopy(ATTACHMENT)
        attachment_1.attachment_id = "attachment_id_1"
        attachment_2.attachment_id = "attachment_id_2"
        attachment_1.raw_data["id"] = attachment_1.attachment_id
        attachment_2.raw_data["id"] = attachment_2.attachment_id
        mimecast.add_attachment(attachment_1)
        mimecast.add_attachment(attachment_2)

        message: HoldMessage = manager.get_hold_message_details(
            subject="TestSubject",
            sender="TestSender",
            recipient="TestRecipient",
            start_time="2023-01-01T00:00:00Z",
            end_time="2023-12-31T23:59:59Z",
        )
        assert len(script_session.request_history) == 7
        assert script_session.request_history[0].response.status_code == 200
        assert script_session.request_history[1].response.status_code == 200
        assert script_session.request_history[2].response.status_code == 200
        assert type(message).__name__ == "HoldMessage"
        assert message.subject == "TestSubject"
        assert message.sender == "TestSender"
        assert len(message.attachments) == 2
