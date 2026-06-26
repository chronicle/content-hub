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

from proof_point_ps.actions import download_quarantined_email
from proof_point_ps.tests.common import CONFIG_PATH

if TYPE_CHECKING:
    from integration_testing.platform.script_output import MockActionOutput

    from proof_point_ps.tests.core.product import ProofPointPSProduct
    from proof_point_ps.tests.core.session import ProofPointPSSession

PARAMETERS_SUCCESS: dict[str, str] = {
    "Message GUIDs": "guid-111",
}


class TestDownloadQuarantinedEmail:
    """Unit tests for DownloadQuarantinedEmail action."""

    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        parameters=PARAMETERS_SUCCESS,
    )
    def test_download_success(
        self,
        script_session: ProofPointPSSession,
        action_output: MockActionOutput,
        proofpoint: ProofPointPSProduct,
    ) -> None:
        """Test successful download of a quarantined email."""
        raw_email = b"Subject: Critical Security Warning\n\nBody content here."
        proofpoint.add_record(
            "Quarantine",
            {"guid": "guid-111", "folder": "Quarantine"},
            raw_content=raw_email,
        )

        download_quarantined_email.main()

        assert len(script_session.request_history) == 6
        assert script_session.request_history[1].request.method.value == "GET"
        assert (
            script_session.request_history[1].request.url.path == "/rest/v1/quarantine"
        )
        assert (
            script_session.request_history[1].request.kwargs["params"]["guid"]
            == "guid-111"
        )

        success_msg = (
            "Successfully downloaded and attached quarantined email raw content "
            "for Message GUID(s): guid-111."
        )
        assert action_output.results is not None
        assert action_output.results.output_message == success_msg
        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert action_output.results.result_value is True
        assert action_output.results.json_output is not None
        assert action_output.results.json_output.json_result == {
            "success": [
                {
                    "processingserver": None,
                    "date": None,
                    "subject": None,
                    "messageid": None,
                    "folder": "Quarantine",
                    "size": None,
                    "rcpts": [],
                    "from": None,
                    "spamscore": None,
                    "guid": "guid-111",
                    "host_ip": None,
                    "localguid": None,
                }
            ]
        }

    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        parameters={
            "Message GUIDs": "guid-111,guid-222",
        },
    )
    def test_download_partial_failure(
        self,
        script_session: ProofPointPSSession,
        action_output: MockActionOutput,
        proofpoint: ProofPointPSProduct,
    ) -> None:
        """Test download where one message succeeds and one fails."""
        raw_email = b"Subject: Critical Security Warning\n\nBody content here."
        proofpoint.add_record(
            "Quarantine",
            {"guid": "guid-111", "folder": "Quarantine"},
            raw_content=raw_email,
        )

        download_quarantined_email.main()

        # pre-validation of guid-222 fails, so it requests folder check, guid-111 check, guid-222 check and stops.
        assert len(script_session.request_history) == 4

        assert action_output.results is not None
        assert (
            'Error executing action "ProofPointPS - Download Quarantined Email"\nReason: Failed to download quarantined email(s). Error:\nThe following message guids were not found in Proofpoint: guid-222.'
            in action_output.results.output_message
        )
        assert action_output.results.execution_state == ExecutionState.FAILED
        assert action_output.results.result_value is False
        assert action_output.results.json_output is None

    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        parameters={
            "Message GUIDs": "guid-222",
        },
    )
    def test_download_complete_failure(
        self,
        script_session: ProofPointPSSession,
        action_output: MockActionOutput,
        proofpoint: ProofPointPSProduct,
    ) -> None:
        """Test complete failure when no messages can be downloaded."""
        download_quarantined_email.main()

        assert len(script_session.request_history) == 2
        assert action_output.results is not None
        assert action_output.results.execution_state == ExecutionState.FAILED
        assert action_output.results.result_value is False
        assert (
            'Error executing action "ProofPointPS - Download Quarantined Email"\nReason: Failed to download quarantined email(s). Error:\nThe following message guids were not found in Proofpoint: guid-222.'
            in action_output.results.output_message
        )
        assert action_output.results.json_output is None
