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

from proof_point_ps.actions import resubmit_quarantined_email
from proof_point_ps.tests.common import CONFIG_PATH

if TYPE_CHECKING:
    from integration_testing.platform.script_output import MockActionOutput

    from proof_point_ps.tests.core.product import ProofPointPSProduct
    from proof_point_ps.tests.core.session import ProofPointPSSession


class TestResubmitQuarantinedEmail:
    """Unit tests for ResubmitQuarantinedEmail action."""

    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        parameters={
            "Message GUIDs": "guid-111",
            "Folder Name": "Quarantine",
        },
    )
    def test_resubmit_success(
        self,
        script_session: ProofPointPSSession,
        action_output: MockActionOutput,
        proofpoint: ProofPointPSProduct,
    ) -> None:
        """Test successful resubmit of a quarantined email."""
        proofpoint.add_record(
            "Quarantine",
            {
                "guid": "guid-111",
                "folder": "Quarantine",
            },
        )

        resubmit_quarantined_email.main()

        assert len(script_session.request_history) == 2
        assert proofpoint.actions_executed[0]["action"] == "resubmit"
        assert proofpoint.actions_executed[0]["localguid"] == "guid-111"

        success_msg = "Successfully resubmitted quarantined email(s): guid-111."
        assert action_output.results is not None
        assert action_output.results.output_message == success_msg
        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert action_output.results.result_value is True

    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        parameters={
            "Message GUIDs": "guid-111",
            "Folder Name": "Quarantine",
        },
    )
    def test_resubmit_validation_failure(
        self,
        script_session: ProofPointPSSession,
        action_output: MockActionOutput,
        proofpoint: ProofPointPSProduct,
    ) -> None:
        """Test resubmit fails when the GUID does not exist in Proofpoint."""
        resubmit_quarantined_email.main()

        assert action_output.results is not None
        assert action_output.results.execution_state == ExecutionState.FAILED
        assert action_output.results.result_value is False
        assert (
            "The following message guids were not found in Proofpoint: guid-111"
            in action_output.results.output_message
        )
