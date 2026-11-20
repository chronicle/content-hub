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

from proof_point_ps.actions import release_quarantined_email
from proof_point_ps.tests.common import CONFIG_PATH

if TYPE_CHECKING:
    from integration_testing.platform.script_output import MockActionOutput

    from proof_point_ps.tests.core.product import ProofPointPSProduct
    from proof_point_ps.tests.core.session import ProofPointPSSession


class TestReleaseQuarantinedEmail:
    """Unit tests for ReleaseQuarantinedEmail action."""

    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        parameters={
            "Message GUIDs": "guid-111",
            "Folder Name": "Quarantine",
            "Deleted Folder Name": "Trash",
            "Rescan Message": "True",
            "Branding Template": "CorporateBranding",
            "Security Policy": "EncryptedPolicy",
        },
    )
    def test_release_success_all_values(
        self,
        script_session: ProofPointPSSession,
        action_output: MockActionOutput,
        proofpoint: ProofPointPSProduct,
    ) -> None:
        """Test successful release of a quarantined email when all parameters are provided."""
        proofpoint.add_record(
            "Quarantine",
            {
                "guid": "guid-111",
                "folder": "Quarantine",
            },
        )
        proofpoint.records["Trash"] = []

        release_quarantined_email.main()

        assert len(script_session.request_history) == 2
        assert proofpoint.actions_executed[0]["action"] == "release"
        assert proofpoint.actions_executed[0]["localguid"] == "guid-111"
        assert proofpoint.actions_executed[0]["deletedfolder"] == "Trash"
        assert proofpoint.actions_executed[0]["scan"] == "t"
        assert proofpoint.actions_executed[0]["brandtemplate"] == "CorporateBranding"
        assert proofpoint.actions_executed[0]["securitypolicy"] == "EncryptedPolicy"

        success_msg = "Successfully released quarantined email(s): guid-111."
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
    def test_release_success_minimal(
        self,
        script_session: ProofPointPSSession,
        action_output: MockActionOutput,
        proofpoint: ProofPointPSProduct,
    ) -> None:
        """Test successful release with only mandatory parameters."""
        proofpoint.add_record(
            "Quarantine",
            {
                "guid": "guid-111",
                "folder": "Quarantine",
            },
        )

        release_quarantined_email.main()

        assert len(script_session.request_history) == 2
        assert proofpoint.actions_executed[0]["action"] == "release"
        assert proofpoint.actions_executed[0]["localguid"] == "guid-111"
        assert "deletedfolder" not in proofpoint.actions_executed[0]
        assert "scan" not in proofpoint.actions_executed[0]

        success_msg = "Successfully released quarantined email(s): guid-111."
        assert action_output.results is not None
        assert action_output.results.output_message == success_msg
        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert action_output.results.result_value is True

    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        parameters={
            "Message GUIDs": "guid-111,guid-222",
            "Folder Name": "Quarantine",
        },
    )
    def test_release_success_multiple_guids(
        self,
        script_session: ProofPointPSSession,
        action_output: MockActionOutput,
        proofpoint: ProofPointPSProduct,
    ) -> None:
        """Test successful release of multiple quarantined emails."""
        proofpoint.add_record(
            "Quarantine",
            {
                "guid": "guid-111",
                "folder": "Quarantine",
            },
        )
        proofpoint.add_record(
            "Quarantine",
            {
                "guid": "guid-222",
                "folder": "Quarantine",
            },
        )

        release_quarantined_email.main()

        # 3 requests: 1 get_records_by_guids, 2 execute_quarantine_action
        assert len(script_session.request_history) == 3
        assert proofpoint.actions_executed[0]["localguid"] == "guid-111"
        assert proofpoint.actions_executed[1]["localguid"] == "guid-222"

        success_msg = "Successfully released quarantined email(s): guid-111, guid-222."
        assert action_output.results is not None
        assert action_output.results.output_message == success_msg
        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert action_output.results.result_value is True

    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        parameters={
            "Message GUIDs": "  guid-111  ,   guid-222   ",
            "Folder Name": "Quarantine",
        },
    )
    def test_release_whitespace_sanitization(
        self,
        script_session: ProofPointPSSession,
        action_output: MockActionOutput,
        proofpoint: ProofPointPSProduct,
    ) -> None:
        """Test whitespace sanitization in GUID inputs."""
        proofpoint.add_record(
            "Quarantine",
            {
                "guid": "guid-111",
                "folder": "Quarantine",
            },
        )
        proofpoint.add_record(
            "Quarantine",
            {
                "guid": "guid-222",
                "folder": "Quarantine",
            },
        )

        release_quarantined_email.main()

        assert proofpoint.actions_executed[0]["localguid"] == "guid-111"
        assert proofpoint.actions_executed[1]["localguid"] == "guid-222"

    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        parameters={
            "Message GUIDs": "guid-111",
            "Folder Name": "Quarantine",
            "Rescan Message": "False",
        },
    )
    def test_release_rescan_disabled(
        self,
        script_session: ProofPointPSSession,
        action_output: MockActionOutput,
        proofpoint: ProofPointPSProduct,
    ) -> None:
        """Test that scan parameter is omitted when Rescan Message is False."""
        proofpoint.add_record(
            "Quarantine",
            {
                "guid": "guid-111",
                "folder": "Quarantine",
            },
        )

        release_quarantined_email.main()

        assert "scan" not in proofpoint.actions_executed[0]

    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        parameters={
            "Message GUIDs": "guid-999",
            "Folder Name": "Quarantine",
        },
    )
    def test_release_non_existent_guid_failure(
        self,
        script_session: ProofPointPSSession,
        action_output: MockActionOutput,
        proofpoint: ProofPointPSProduct,
    ) -> None:
        """Test release fails when the GUID does not exist."""
        release_quarantined_email.main()

        assert action_output.results is not None
        assert action_output.results.execution_state == ExecutionState.FAILED
        assert action_output.results.result_value is False
        assert (
            "The following message guids were not found in Proofpoint: guid-999."
            in action_output.results.output_message
        )

    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        parameters={
            "Message GUIDs": "guid-111,guid-999",
            "Folder Name": "Quarantine",
        },
    )
    def test_release_mixed_guids_failure(
        self,
        script_session: ProofPointPSSession,
        action_output: MockActionOutput,
        proofpoint: ProofPointPSProduct,
    ) -> None:
        """Test release fails when there is a mix of valid and invalid GUIDs."""
        proofpoint.add_record(
            "Quarantine",
            {
                "guid": "guid-111",
                "folder": "Quarantine",
            },
        )

        release_quarantined_email.main()

        assert action_output.results is not None
        assert action_output.results.execution_state == ExecutionState.FAILED
        assert action_output.results.result_value is False
        assert (
            "The following message guids were not found in Proofpoint: guid-999."
            in action_output.results.output_message
        )

    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        parameters={
            "Message GUIDs": "guid-111",
            "Folder Name": "InvalidFolder",
        },
    )
    def test_release_invalid_folder_failure(
        self,
        script_session: ProofPointPSSession,
        action_output: MockActionOutput,
        proofpoint: ProofPointPSProduct,
    ) -> None:
        """Test release fails when the source folder does not exist."""
        release_quarantined_email.main()

        assert action_output.results is not None
        assert action_output.results.execution_state == ExecutionState.FAILED
        assert action_output.results.result_value is False
        assert (
            "Folder 'InvalidFolder' does not exist."
            in action_output.results.output_message
        )

    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        parameters={
            "Message GUIDs": "guid-111",
            "Folder Name": "Quarantine",
            "Deleted Folder Name": "InvalidTrash",
        },
    )
    def test_release_invalid_deleted_folder_failure(
        self,
        script_session: ProofPointPSSession,
        action_output: MockActionOutput,
        proofpoint: ProofPointPSProduct,
    ) -> None:
        """Test release fails when the deleted folder does not exist."""
        proofpoint.add_record(
            "Quarantine",
            {
                "guid": "guid-111",
                "folder": "Quarantine",
            },
        )

        release_quarantined_email.main()

        assert action_output.results is not None
        assert action_output.results.execution_state == ExecutionState.FAILED
        assert action_output.results.result_value is False
        assert (
            "Deleted folder 'InvalidTrash' does not exist."
            in action_output.results.output_message
        )

    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        parameters={
            "Message GUIDs": "guid-111",
            "Folder Name": "Quarantine",
            "Deleted Folder Name": "Quarantine",
        },
    )
    def test_release_same_folder_error(
        self,
        script_session: ProofPointPSSession,
        action_output: MockActionOutput,
        proofpoint: ProofPointPSProduct,
    ) -> None:
        """Test release fails when deleted folder is the same as source folder."""
        release_quarantined_email.main()

        assert action_output.results is not None
        assert action_output.results.execution_state == ExecutionState.FAILED
        assert action_output.results.result_value is False
        assert (
            "Folder and deleted folder cannot be the same"
            in action_output.results.output_message
        )
