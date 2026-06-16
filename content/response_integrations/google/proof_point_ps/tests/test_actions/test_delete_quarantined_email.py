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

from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata
from proof_point_ps.actions import delete_quarantined_email
from proof_point_ps.tests.common import CONFIG_PATH
from proof_point_ps.tests.core.product import ProofPointPSProduct
from proof_point_ps.tests.core.session import ProofPointPSSession
from TIPCommon.base.action import ExecutionState

PARAMETERS_SUCCESS: dict[str, str] = {
    "Message GUIDs": "guid-111,guid-222",
    "Folder Name": "Quarantine",
    "Deleted Folder Name": "Trash",
    "Time Frame": "Last Hour",
}


class TestDeleteQuarantinedEmail:
    """Unit tests for DeleteQuarantinedEmail action."""

    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        parameters=PARAMETERS_SUCCESS,
    )
    def test_delete_success(
        self,
        script_session: ProofPointPSSession,
        action_output: MockActionOutput,
        proofpoint: ProofPointPSProduct,
    ) -> None:
        """Test successful deletion of all requested quarantined emails."""
        proofpoint.add_record(
            "Quarantine",
            {
                "guid": "guid-111",
                "localguid": "local-111",
                "folder": "Quarantine",
            },
        )
        proofpoint.add_record(
            "Quarantine",
            {
                "guid": "guid-222",
                "localguid": "local-222",
                "folder": "Quarantine",
            },
        )

        delete_quarantined_email.main()

        assert len(script_session.request_history) == 3
        assert proofpoint.actions_executed[0]["action"] == "delete"
        assert proofpoint.actions_executed[0]["localguid"] == "guid-111"
        assert proofpoint.actions_executed[1]["localguid"] == "guid-222"

        success_msg = (
            "Successfully deleted quarantined email(s): guid-111, guid-222"
        )
        assert action_output.results.output_message == success_msg
        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert action_output.results.result_value is True

    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        parameters={
            "Message GUIDs": "guid-111,guid-333",
            "Folder Name": "Quarantine",
            "Time Frame": "Last Hour",
        },
    )
    def test_delete_partial_failure(
        self,
        script_session: ProofPointPSSession,
        action_output: MockActionOutput,
        proofpoint: ProofPointPSProduct,
    ) -> None:
        """Test deletion where one message is found and one is not."""
        proofpoint.add_record(
            "Quarantine", {"guid": "guid-111", "folder": "Quarantine"}
        )

        delete_quarantined_email.main()

        assert len(script_session.request_history) == 2
        assert len(proofpoint.actions_executed) == 1
        assert proofpoint.actions_executed[0]["localguid"] == "guid-111"

        partial_msg = (
            "Failed to delete some quarantined emails. Successfully deleted: "
            "guid-111. Failed for: guid-333 (Error: Message not found)"
        )
        assert action_output.results.output_message == partial_msg
        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert action_output.results.result_value is False

    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        parameters={
            "Message GUIDs": "guid-444",
            "Folder Name": "Quarantine",
            "Time Frame": "Last Hour",
        },
    )
    def test_delete_complete_failure(
        self,
        script_session: ProofPointPSSession,
        action_output: MockActionOutput,
        proofpoint: ProofPointPSProduct,
    ) -> None:
        """Test complete failure when no messages are found to delete."""
        delete_quarantined_email.main()

        assert action_output.results.execution_state == ExecutionState.FAILED
        assert (
            "Failed to delete any quarantined emails"
            in action_output.results.output_message
        )
