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

import os
import pathlib
import shutil
from typing import TYPE_CHECKING

from integration_testing.set_meta import set_metadata
from TIPCommon.base.action import ExecutionState

from proof_point_ps.actions import download_quarantined_email
from proof_point_ps.tests.common import CONFIG_PATH

if TYPE_CHECKING:
    from integration_testing.platform.script_output import MockActionOutput

    from proof_point_ps.tests.core.product import ProofPointPSProduct
    from proof_point_ps.tests.core.session import ProofPointPSSession

TEST_DIR = "/tmp/proofpoint_test_download"


class TestDownloadQuarantinedEmail:
    """Unit tests for DownloadQuarantinedEmail action."""

    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        parameters={
            "Message GUIDs": "guid-111",
            "Download Folder Path": TEST_DIR,
            "Overwrite": "True",
            "Save To Case Wall": "True",
        },
    )
    def test_download_success(
        self,
        script_session: ProofPointPSSession,
        action_output: MockActionOutput,
        proofpoint: ProofPointPSProduct,
    ) -> None:
        """Test successful download of a quarantined email."""
        os.makedirs(TEST_DIR, exist_ok=True)
        target_file = pathlib.Path(TEST_DIR) / "guid-111-Critical_Security_Warning.eml"
        if target_file.exists():
            target_file.unlink()

        raw_email = b"Subject: Critical Security Warning\n\nBody content here."
        proofpoint.add_record(
            "Quarantine",
            {"guid": "guid-111", "folder": "Quarantine"},
            raw_content=raw_email,
        )

        try:
            download_quarantined_email.main()

            assert len(script_session.request_history) == 3
            assert script_session.request_history[1].request.method.value == "GET"
            assert (
                script_session.request_history[1].request.url.path == "/rest/v1/quarantine"
            )
            assert (
                script_session.request_history[1].request.kwargs["params"]["guid"]
                == "guid-111"
            )

            success_msg = (
                "Successfully downloaded quarantined email raw content "
                "for Message GUID(s): guid-111."
            )
            assert action_output.results is not None
            assert action_output.results.output_message == success_msg
            assert action_output.results.execution_state == ExecutionState.COMPLETED
            assert action_output.results.result_value is True
            assert target_file.exists()
            assert target_file.read_bytes() == raw_email
            assert action_output.results.json_output is not None
            assert action_output.results.json_output.json_result == {
                "success": [
                    {
                        "downloaded_file_path": str(
                            pathlib.Path(TEST_DIR)
                            / "guid-111-Critical_Security_Warning.eml"
                        ),
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
        finally:
            shutil.rmtree(TEST_DIR, ignore_errors=True)

    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        parameters={
            "Message GUIDs": "guid-111",
            "Download Folder Path": TEST_DIR,
            "Overwrite": "False",
            "Save To Case Wall": "False",
        },
    )
    def test_download_overwrite_false_file_exists(
        self,
        script_session: ProofPointPSSession,
        action_output: MockActionOutput,
        proofpoint: ProofPointPSProduct,
    ) -> None:
        """Test download fails when Overwrite is False and target file already exists."""
        os.makedirs(TEST_DIR, exist_ok=True)
        target_file = pathlib.Path(TEST_DIR) / "guid-111-Critical_Security_Warning.eml"
        target_file.write_bytes(b"Existing content")

        raw_email = b"Subject: Critical Security Warning\n\nBody content here."
        proofpoint.add_record(
            "Quarantine",
            {"guid": "guid-111", "folder": "Quarantine"},
            raw_content=raw_email,
        )

        try:
            download_quarantined_email.main()

            assert action_output.results is not None
            assert action_output.results.execution_state == ExecutionState.FAILED
            assert action_output.results.result_value is False
            assert (
                f"File '{target_file}' already exists. "
                f"Please change the path or set parameter 'Overwrite' to True."
                in action_output.results.output_message
            )
            # The file should not be overwritten
            assert target_file.read_bytes() == b"Existing content"
        finally:
            shutil.rmtree(TEST_DIR, ignore_errors=True)

    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        parameters={
            "Message GUIDs": "guid-111",
            "Download Folder Path": "/non_existent_folder_xyz",
            "Overwrite": "True",
            "Save To Case Wall": "False",
        },
    )
    def test_download_folder_not_exist(
        self,
        script_session: ProofPointPSSession,
        action_output: MockActionOutput,
        proofpoint: ProofPointPSProduct,
    ) -> None:
        """Test download fails when the destination folder does not exist."""
        raw_email = b"Subject: Critical Security Warning\n\nBody content here."
        proofpoint.add_record(
            "Quarantine",
            {"guid": "guid-111", "folder": "Quarantine"},
            raw_content=raw_email,
        )

        download_quarantined_email.main()

        assert action_output.results is not None
        assert action_output.results.execution_state == ExecutionState.FAILED
        assert action_output.results.result_value is False
        assert (
            "Download folder path '/non_existent_folder_xyz' does not exist or is not a directory."
            in action_output.results.output_message
        )

    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        parameters={
            "Message GUIDs": "guid-111,guid-222",
            "Download Folder Path": TEST_DIR,
            "Overwrite": "True",
            "Save To Case Wall": "False",
        },
    )
    def test_download_partial_failure(
        self,
        script_session: ProofPointPSSession,
        action_output: MockActionOutput,
        proofpoint: ProofPointPSProduct,
    ) -> None:
        """Test download where one message succeeds and one fails."""
        os.makedirs(TEST_DIR, exist_ok=True)
        raw_email = b"Subject: Critical Security Warning\n\nBody content here."
        proofpoint.add_record(
            "Quarantine",
            {"guid": "guid-111", "folder": "Quarantine"},
            raw_content=raw_email,
        )

        try:
            download_quarantined_email.main()

            # pre-validation of guid-222 fails, so it requests folder check,
            # guid-111 check, guid-222 check and stops.
            assert len(script_session.request_history) == 2

            assert action_output.results is not None
            assert (
                'Error executing action "ProofPointPS - Download Quarantined Email"\n'
                'Reason: The following message guids were not found in Proofpoint: guid-222.'
                in action_output.results.output_message
            )
            assert action_output.results.execution_state == ExecutionState.FAILED
            assert action_output.results.result_value is False
            assert action_output.results.json_output is None
        finally:
            shutil.rmtree(TEST_DIR, ignore_errors=True)

    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        parameters={
            "Message GUIDs": "guid-111,guid-222",
            "Download Folder Path": TEST_DIR,
            "Overwrite": "False",
            "Save To Case Wall": "False",
        },
    )
    def test_download_multiple_file_collisions(
        self,
        script_session: ProofPointPSSession,
        action_output: MockActionOutput,
        proofpoint: ProofPointPSProduct,
    ) -> None:
        """Test download where multiple files already exist and overwrite is False."""
        os.makedirs(TEST_DIR, exist_ok=True)
        raw_email1 = b"Subject: First Mail\n\nBody content."
        raw_email2 = b"Subject: Second Mail\n\nBody content."
        proofpoint.add_record(
            "Quarantine",
            {"guid": "guid-111", "folder": "Quarantine"},
            raw_content=raw_email1,
        )
        proofpoint.add_record(
            "Quarantine",
            {"guid": "guid-222", "folder": "Quarantine"},
            raw_content=raw_email2,
        )

        target_file1 = pathlib.Path(TEST_DIR) / "guid-111-First_Mail.eml"
        target_file2 = pathlib.Path(TEST_DIR) / "guid-222-Second_Mail.eml"
        target_file1.write_bytes(b"Existing content 1")
        target_file2.write_bytes(b"Existing content 2")

        try:
            download_quarantined_email.main()

            assert action_output.results is not None
            assert action_output.results.execution_state == ExecutionState.FAILED
            assert action_output.results.result_value is False
            assert (
                "GUIDs guid-111, guid-222 failed during execution. "
                "Error: File already exists. "
                "Please change the path or set parameter 'Overwrite' to True."
                in action_output.results.output_message
            )
            assert target_file1.read_bytes() == b"Existing content 1"
            assert target_file2.read_bytes() == b"Existing content 2"
        finally:
            shutil.rmtree(TEST_DIR, ignore_errors=True)
