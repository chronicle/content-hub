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

import datetime
import pytest
from typing import TYPE_CHECKING

from integration_testing.common import create_entity
from integration_testing.set_meta import set_metadata
from TIPCommon.base.action import EntityTypesEnum, ExecutionState
from TIPCommon.consts import NUM_OF_MILLI_IN_SEC

from proof_point_ps.actions import search_quarantined_emails
from proof_point_ps.tests.common import CONFIG_PATH

if TYPE_CHECKING:
    from integration_testing.platform.script_output import MockActionOutput

    from proof_point_ps.tests.core.product import ProofPointPSProduct
    from proof_point_ps.tests.core.session import ProofPointPSSession

USER_ENTITY = create_entity("test_user@example.com", EntityTypesEnum.USER)


def get_deadline_context() -> dict:
    """Return an input context dict with a future execution deadline."""
    deadline = datetime.datetime.now() + datetime.timedelta(minutes=10)
    return {
        "execution_deadline_unix_time_ms": int(
            deadline.timestamp() * NUM_OF_MILLI_IN_SEC
        )
    }


class TestSearchQuarantinedEmails:
    """Unit tests for SearchQuarantinedEmails action."""

    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        entities=[],
        input_context=get_deadline_context(),
        parameters={
            "Time Frame": "Last 24 Hours",
            "Folder Name": "Quarantine",
            "Fetch DLP Violation": "No",
            "Fetch Message Status": False,
            "Max Results To Return": "100",
            "Subject": "Lottery",
        }
    )
    def test_search_by_subject_exact_match(
        self,
        script_session: ProofPointPSSession,
        action_output: MockActionOutput,
        proofpoint: ProofPointPSProduct,
    ) -> None:
        """Test searching with exact subject match."""
        record1 = {
            "processingserver": "pps-server-01",
            "date": "2026-06-21T12:00:00Z",
            "subject": "Lottery",
            "messageid": "msg-123",
            "folder": "Quarantine",
            "size": 1000,
            "rcpts": ["rcpt@example.com"],
            "from": "sender@example.com",
            "spamscore": 0,
            "guid": "guid-123",
            "host_ip": "1.1.1.1",
            "localguid": "guid-123",
            "dlpviolation": "Not Applicable",
        }
        record2 = {
            "processingserver": "pps-server-01",
            "date": "2026-06-21T12:00:00Z",
            "subject": "Lottery Winning 3",
            "messageid": "msg-456",
            "folder": "Quarantine",
            "size": 2000,
            "rcpts": ["rcpts@example.com"],
            "from": "sender@example.com",
            "spamscore": 0,
            "guid": "guid-456",
            "host_ip": "1.1.1.1",
            "localguid": "guid-456",
            "dlpviolation": "Not Applicable",
        }
        proofpoint.add_record("Quarantine", record1)
        proofpoint.add_record("Quarantine", record2)

        search_quarantined_emails.main()

        assert action_output.results is not None
        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert action_output.results.json_output is not None

        json_results = action_output.results.json_output.json_result
        assert isinstance(json_results, list)
        assert len(json_results) == 1
        assert json_results[0]["subject"] == "Lottery"
        assert json_results[0]["messageid"] == "msg-123"

    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        entities=[],
        input_context=get_deadline_context(),
        parameters={
            "Time Frame": "Last 24 Hours",
            "Folder Name": "Quarantine",
            "Message ID": "msg-123",
            "Fetch DLP Violation": "No",
            "Fetch Message Status": False,
            "Max Results To Return": "100",
        }
    )
    def test_search_by_message_id_success(
        self,
        script_session: ProofPointPSSession,
        action_output: MockActionOutput,
        proofpoint: ProofPointPSProduct,
    ) -> None:
        """Test searching with Message ID returns only matching record."""
        record1 = {
            "processingserver": "pps-server-01",
            "date": "2026-06-21T12:00:00Z",
            "subject": "Test",
            "messageid": "msg-123",
            "folder": "Quarantine",
            "size": 1000,
            "rcpts": ["rcpt@example.com"],
            "from": "sender@example.com",
            "spamscore": 0,
            "guid": "guid-123",
            "host_ip": "1.1.1.1",
            "localguid": "guid-123",
            "dlpviolation": "Not Applicable",
        }
        record2 = {
            "processingserver": "pps-server-01",
            "date": "2026-06-21T12:00:00Z",
            "subject": "Test",
            "messageid": "msg-789",
            "folder": "Quarantine",
            "size": 2000,
            "rcpts": ["rcpt@example.com"],
            "from": "sender@example.com",
            "spamscore": 0,
            "guid": "guid-789",
            "host_ip": "1.1.1.1",
            "localguid": "guid-789",
            "dlpviolation": "Not Applicable",
        }
        proofpoint.add_record("Quarantine", record1)
        proofpoint.add_record("Quarantine", record2)

        search_quarantined_emails.main()

        assert action_output.results is not None
        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert action_output.results.json_output is not None

        json_results = action_output.results.json_output.json_result
        assert isinstance(json_results, list)
        assert len(json_results) == 1
        assert json_results[0]["messageid"] == "msg-123"

    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        entities=[],
        input_context=get_deadline_context(),
        parameters={
            "Time Frame": "Last 24 Hours",
            "Folder Name": "Quarantine",
            "Fetch DLP Violation": "Basic",
            "Fetch Message Status": False,
            "Max Results To Return": "100",
        }
    )
    def test_search_dlp_violation_filter_basic(
        self,
        script_session: ProofPointPSSession,
        action_output: MockActionOutput,
        proofpoint: ProofPointPSProduct,
    ) -> None:
        """Test searching with Fetch DLP Violation set to Basic returns only records with Basic DLP violation."""
        record1 = {
            "processingserver": "pps-server-01",
            "date": "2026-06-21T12:00:00Z",
            "subject": "Test",
            "messageid": "msg-123",
            "folder": "Quarantine",
            "size": 1000,
            "rcpts": ["rcpt@example.com"],
            "from": "sender@example.com",
            "spamscore": 0,
            "guid": "guid-123",
            "host_ip": "1.1.1.1",
            "localguid": "guid-123",
            "dlpviolation": "Not Applicable",
        }
        record2 = {
            "processingserver": "pps-server-01",
            "date": "2026-06-21T12:00:00Z",
            "subject": "Test Violation",
            "messageid": "msg-789",
            "folder": "Quarantine",
            "size": 2000,
            "rcpts": ["rcpt@example.com"],
            "from": "sender@example.com",
            "spamscore": 0,
            "guid": "guid-789",
            "host_ip": "1.1.1.1",
            "localguid": "guid-789",
            "dlpviolation": "t",
        }
        proofpoint.add_record("Quarantine", record1)
        proofpoint.add_record("Quarantine", record2)

        search_quarantined_emails.main()

        assert action_output.results is not None
        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert action_output.results.json_output is not None

        json_results = action_output.results.json_output.json_result
        assert isinstance(json_results, list)
        assert len(json_results) == 1
        assert json_results[0]["messageid"] == "msg-789"
        assert json_results[0]["dlpviolation"] == "t"

    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        entities=[],
        input_context=get_deadline_context(),
        parameters={
            "Time Frame": "Last 24 Hours",
            "Folder Name": "Quarantine",
            "Fetch DLP Violation": "Detailed",
            "Fetch Message Status": False,
            "Max Results To Return": "100",
        }
    )
    def test_search_dlp_violation_filter_detailed(
        self,
        script_session: ProofPointPSSession,
        action_output: MockActionOutput,
        proofpoint: ProofPointPSProduct,
    ) -> None:
        """Test searching with Fetch DLP Violation set to Detailed returns only records with Detailed DLP violation."""
        record1 = {
            "processingserver": "pps-server-01",
            "date": "2026-06-21T12:00:00Z",
            "subject": "Test",
            "messageid": "msg-123",
            "folder": "Quarantine",
            "size": 1000,
            "rcpts": ["rcpt@example.com"],
            "from": "sender@example.com",
            "spamscore": 0,
            "guid": "guid-123",
            "host_ip": "1.1.1.1",
            "localguid": "guid-123",
            "dlpviolation": "Not Applicable",
        }
        record2 = {
            "processingserver": "pps-server-01",
            "date": "2026-06-21T12:00:00Z",
            "subject": "Test Violation",
            "messageid": "msg-789",
            "folder": "Quarantine",
            "size": 2000,
            "rcpts": ["rcpt@example.com"],
            "from": "sender@example.com",
            "spamscore": 0,
            "guid": "guid-789",
            "host_ip": "1.1.1.1",
            "localguid": "guid-789",
            "dlpviolation": {
                "rule": "Rule A",
                "action": "Block",
            },
        }
        proofpoint.add_record("Quarantine", record1)
        proofpoint.add_record("Quarantine", record2)

        search_quarantined_emails.main()

        assert action_output.results is not None
        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert action_output.results.json_output is not None

        json_results = action_output.results.json_output.json_result
        assert isinstance(json_results, list)
        assert len(json_results) == 1
        assert json_results[0]["messageid"] == "msg-789"
        assert isinstance(json_results[0]["dlpviolation"], dict)

    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        entities=[],
        input_context=get_deadline_context(),
        parameters={
            "Time Frame": "Last 24 Hours",
            "Folder Name": "Quarantine",
            "Fetch DLP Violation": "No",
            "Fetch Message Status": False,
            "Max Results To Return": "-5",
        }
    )
    def test_search_invalid_limit(
        self,
        script_session: ProofPointPSSession,
        action_output: MockActionOutput,
        proofpoint: ProofPointPSProduct,
    ) -> None:
        """Test search with invalid non-positive limit parameter fails."""
        search_quarantined_emails.main()

        assert action_output.results is not None
        assert action_output.results.execution_state == ExecutionState.FAILED
        assert action_output.results.result_value is False
        assert (
            'Error executing action "ProofPointPS - Search Quarantined Emails"\nReason: Failed to search quarantined email(s) (Error: "Max Results To Return" must be greater than 0.)'
            in action_output.results.output_message
        )
        assert action_output.results.json_output is None
