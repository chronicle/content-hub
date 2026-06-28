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
from TIPCommon.base.action import ExecutionState
from TIPCommon.types import SingleJson

from mimecast.actions import CreateBlockSenderPolicy

from mimecast.tests.common import CONFIG_PATH, MOCK_DATA
from mimecast.tests.core.session import MimecastSession
from mimecast.tests.core.product import Mimecast
COMMENT = "test comment"
from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata


SUCCESS_PARAMS: SingleJson = {
    "Response": "Block Sender",
    "Description": "Test Policy",
    "Extracted Data": "Both",
    "Sender": "test@example.com",
    "Sender Type": "Email Address",
    "Recipient": "recipient@example.com",
    "Recipient Type": "Email Address",
    "Comment": COMMENT,
    "Bidirectional": False,
    "Enforced": True,
    "Start Time": "",
    "End Time": "",
}
FAILED_PARAMS: SingleJson = {
    "Response": "Block Sender",
    "Description": "Test Policy",
    "Extracted Data": "Both",
    "Sender": "test@example.com",
    "Sender Type": "Email Address",
    "Recipient": "recipient@example.com",
    "Recipient Type": "Email Address",
    "Comment": "wrong_format",
    "Bidirectional": False,
    "Enforced": True,
    "Start Time": "",
    "End Time": "",
}

SUCCESS_OUTPUT_MESSAGE: str = "Successfully created a block sender policy in Mimecast"
FAILURE_OUTPUT_MESSAGE: str = (
    "Error executing action \"Mimecast - Create Block Sender Policy\""
    ".\nReason: An error occurred: Invalid fromValue"
)


class TestHappyPath:

    @set_metadata(
        parameters=SUCCESS_PARAMS,
        integration_config_file_path=CONFIG_PATH,
    )
    def test_create_block_sender_policy_success(
        self,
        mimecast: Mimecast,
        script_session: MimecastSession,
        action_output: MockActionOutput,
    ) -> None:
        mimecast.add_block_policy(
            MOCK_DATA["create_block_sender_policy_success"]["data"][0]
        )

        CreateBlockSenderPolicy.main()

        assert len(script_session.request_history) == 2
        assert action_output.results.output_message == SUCCESS_OUTPUT_MESSAGE
        assert action_output.results.result_value is True
        assert action_output.results.execution_state == ExecutionState.COMPLETED


    @set_metadata(
        parameters=FAILED_PARAMS,
        integration_config_file_path=CONFIG_PATH,
    )
    def test_create_block_sender_policy_failed(
            self,
            script_session: MimecastSession,
            action_output: MockActionOutput,
    ) -> None:
        CreateBlockSenderPolicy.main()

        assert len(script_session.request_history) == 2
        assert action_output.results.output_message == FAILURE_OUTPUT_MESSAGE
        assert action_output.results.result_value is False
        assert action_output.results.execution_state == ExecutionState.FAILED
