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

from typing import TYPE_CHECKING

from integration_testing.set_meta import set_metadata
from TIPCommon.base.action import ExecutionState

from proof_point_ps.actions import forward_quarantined_email
from proof_point_ps.tests.common import CONFIG_PATH

if TYPE_CHECKING:
    from integration_testing.platform.script_output import MockActionOutput

    from proof_point_ps.tests.core.product import ProofPointPSProduct
    from proof_point_ps.tests.core.session import ProofPointPSSession


class TestForwardQuarantinedEmail:
    """Unit tests for ForwardQuarantinedEmail action."""

    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        parameters={
            "Message GUIDs": "guid-111",
            "Folder Name": "Quarantine",
            "Deleted Folder Name": "Trash",
            "To Address": "recipient@example.com",
        },
    )
    def test_forward_success(
        self,
        script_session: ProofPointPSSession,
        action_output: MockActionOutput,
        proofpoint: ProofPointPSProduct,
    ) -> None:
        """Test successful forward of a quarantined email."""
        proofpoint.add_record(
            "Quarantine",
            {
                "guid": "guid-111",
                "folder": "Quarantine",
            },
        )
        proofpoint.records["Trash"] = []

        forward_quarantined_email.main()

        assert len(script_session.request_history) == 3
        assert proofpoint.actions_executed[0]["action"] == "forward"
        assert proofpoint.actions_executed[0]["localguid"] == "guid-111"

        success_msg = "Successfully forwarded quarantined email(s): guid-111."
        assert action_output.results is not None
        assert action_output.results.output_message == success_msg
        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert action_output.results.result_value is True

    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        parameters={
            "Message GUIDs": "guid-111",
            "Folder Name": "Quarantine",
            "Deleted Folder Name": "Quarantine",
            "To Address": "recipient@example.com",
        },
    )
    def test_forward_same_folder_error(
        self,
        script_session: ProofPointPSSession,
        action_output: MockActionOutput,
        proofpoint: ProofPointPSProduct,
    ) -> None:
        """Test forward fails when deleted folder is the same as source folder."""
        forward_quarantined_email.main()

        assert action_output.results is not None
        assert action_output.results.execution_state == ExecutionState.FAILED
        assert action_output.results.result_value is False
        assert (
            "Folder and deleted folder cannot be the same"
            in action_output.results.output_message
        )
