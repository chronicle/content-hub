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

"""Unit tests for the CrowdStrikeFalcon List Host Vulnerabilities action."""
from __future__ import annotations

import copy
from typing import Any

import pytest
from crowd_strike_falcon.actions import ListHostVulnerabilities
from TIPCommon.base.action import EntityTypesEnum, ExecutionState
from TIPCommon.types import Entity, SingleJson

from crowd_strike_falcon.tests.common import (
    CONFIG_PATH,
    HOSTNAME_ENTITY,
    HOSTNAME_ENTITY_ID,
    MOCK_DATA,
)
from crowd_strike_falcon.tests.core.crowd_strike_falcon import CrowdStrikeFalcon
from crowd_strike_falcon.tests.core.session import CrowdStrikeFalconSession
from integration_testing.common import create_entity
from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata

WRONG_ENTITY_ID: str = "npatni-sysops"
WRONG_ENTITY: Entity = create_entity(WRONG_ENTITY_ID, EntityTypesEnum.IP_SET)

FILE_PATH_SCAN: str = r"C:\Windows"
CPU_PRIORITY: str = "Up to 25% CPU utilization"
MODERATE: str = "Moderate"
TRUE: bool = True
BASE_PARAMS: SingleJson = {
    "File Paths To Scan": FILE_PATH_SCAN,
    "File Paths To Exclude From Scan": "",
    "Host Group Name": "",
    "Scan Description": "",
    "CPU Priority": CPU_PRIORITY,
    "Sensor Anti-malware Detection Level": MODERATE,
    "Sensor Anti-malware Prevention Level": MODERATE,
    "Cloud Anti-malware Detection Level": MODERATE,
    "Cloud Anti-malware Prevention Level": MODERATE,
    "Quarantine Hosts": TRUE,
    "Create Endpoint Notification": TRUE,
    "Max Scan Duration": 1,
}
SUCCESS_OUTPUT_MESSAGE: str = (
    "Successfully retrieved vulnerabilities for the following hosts: "
    f"{HOSTNAME_ENTITY_ID}\n"
)
FAILURE_OUTPUT_MESSAGE: str = "No vulnerabilities were found."

ACTION_CUSTOMER_ID: str = "action_cid_123"
INTEGRATION_CUSTOMER_ID: str = "integration_cid_456"

BASE_PARAMS_FOR_CID_TESTS: SingleJson = {
    "Create Insight": True,
    "Max Vulnerabilities To Return": 5,
    "Severity Filter": "",
}

PARENT_TENANT_PARAMS: SingleJson = {**BASE_PARAMS_FOR_CID_TESTS, "Customer ID": ""}
CHILD_TENANT_PARAMS: SingleJson = {
    **BASE_PARAMS_FOR_CID_TESTS,
    "Customer ID": ACTION_CUSTOMER_ID,
}
DEVICE_ID_PARAMS: SingleJson = {
    **BASE_PARAMS_FOR_CID_TESTS,
    "Customer ID": "",
    "Device ID": "2a1c5ef609ac479ba77f8ca5879c82fc",
}

INTEGRATION_CONFIG_WITH_CID: SingleJson = {
    "API Root": "https://api.crowdstrike.com",
    "Client API ID": "dummy",
    "Client API Secret": "dummy",
    "Verify SSL": "False",
    "Customer ID": INTEGRATION_CUSTOMER_ID,
}

PENDING_ODS_SCAN_MOCK = copy.deepcopy(MOCK_DATA["get_ods_entities_scans"])
PENDING_ODS_SCAN_MOCK["resources"][0]["status"] = "pending"


@pytest.fixture
def setup_crowdstrike_data_completed(
    crowd_strike_falcon: CrowdStrikeFalcon,
) -> None:
    """Prepare mock data for a scan that completes immediately."""
    crowd_strike_falcon.add_device(MOCK_DATA["get_devices"]["resources"][0])
    crowd_strike_falcon.add_on_demand_scan(
        MOCK_DATA["get_ods_entities_scans"],
    )


@pytest.fixture
def setup_crowdstrike_data_pending(
    crowd_strike_falcon: CrowdStrikeFalcon,
) -> None:
    """Prepare mock data for a scan that remains in a pending state."""
    crowd_strike_falcon.add_device(MOCK_DATA["get_devices"]["resources"][0])
    crowd_strike_falcon.add_on_demand_scan(PENDING_ODS_SCAN_MOCK)


@pytest.mark.usefixtures("script_session")
class TestHappyPath:
    """Tests for the action's happy paths."""

    @set_metadata(
        parameters=copy.deepcopy(DEVICE_ID_PARAMS),
        entities=[],
        integration_config_file_path=CONFIG_PATH,
    )
    def test_list_hosts_vulnerabilities_with_device_id_success(
        self,
        crowd_strike_falcon: CrowdStrikeFalcon,
        action_output: MockActionOutput,
    ) -> None:
        """Tests a successful run of listing host vulnerabilities with device ID."""
        crowd_strike_falcon.add_device(MOCK_DATA["get_devices"]["resources"][0])
        crowd_strike_falcon.add_entries(
            "vulnerabilities",
            MOCK_DATA["spotlight_entities_vulnerabilities_v2"]["resources"],
        )

        ListHostVulnerabilities.main()

        assert action_output.results.output_message == "Successfully retrieved vulnerabilities for the following hosts: 2a1c5ef609ac479ba77f8ca5879c82fc\n"
        assert action_output.results.result_value is True
        assert action_output.results.execution_state == ExecutionState.COMPLETED

    @set_metadata(
        parameters=BASE_PARAMS,
        entities=[HOSTNAME_ENTITY],
        integration_config_file_path=CONFIG_PATH,
    )
    def test_list_hosts_vulnerabilities_success(
        self,
        script_session: CrowdStrikeFalconSession,
        crowd_strike_falcon: CrowdStrikeFalcon,
        action_output: MockActionOutput,
    ) -> None:
        """Tests a successful run of listing host vulnerabilities."""
        crowd_strike_falcon.add_entries(
            "vulnerabilities",
            MOCK_DATA["spotlight_entities_vulnerabilities_v2"]["resources"],
        )

        ListHostVulnerabilities.main()

        assert len(script_session.request_history) == 6
        assert action_output.results.output_message == SUCCESS_OUTPUT_MESSAGE
        assert action_output.results.result_value is True
        assert action_output.results.execution_state == ExecutionState.COMPLETED

    @set_metadata(
        parameters=BASE_PARAMS,
        entities=[WRONG_ENTITY],
        integration_config_file_path=CONFIG_PATH,
    )
    def test_list_hosts_vulnerabilities_wrong_entity(
        self,
        script_session: CrowdStrikeFalconSession,
        action_output: MockActionOutput,
    ) -> None:
        """Tests the action's behavior with an unsupported entity type."""
        ListHostVulnerabilities.main()

        assert len(script_session.request_history) == 2
        assert action_output.results.output_message == FAILURE_OUTPUT_MESSAGE
        assert action_output.results.result_value is False
        assert action_output.results.execution_state == ExecutionState.COMPLETED


@pytest.fixture
def setup_crowdstrike_data(crowd_strike_falcon: CrowdStrikeFalcon) -> None:
    """Prepare mock data for tests."""
    crowd_strike_falcon.add_device(MOCK_DATA["get_devices"]["resources"][0])
    crowd_strike_falcon.add_vulnerability(
        MOCK_DATA["spotlight_entities_vulnerabilities_v2"]["resources"][0],
    )


@pytest.mark.usefixtures("script_session", "setup_crowdstrike_data")
class TestMemberCID:
    """Tests for Customer ID (member_cid) functionality."""

    @set_metadata(
        parameters=PARENT_TENANT_PARAMS,
        entities=[HOSTNAME_ENTITY],
        integration_config_file_path=CONFIG_PATH,
    )
    def test_parent_tenant_auth_when_no_cid_is_provided(
        self,
        script_session: CrowdStrikeFalconSession,
        action_output: MockActionOutput,
    ) -> None:
        """Tests that auth targets the parent tenant when no Customer ID is given."""
        ListHostVulnerabilities.main()
        history_record: Any = script_session.request_history[0]
        token_request_payload: dict[str, Any] = history_record.request.kwargs.get(
            "data", {},
        )
        assert "member_cid" not in token_request_payload
        assert action_output.results.execution_state == ExecutionState.COMPLETED

    @set_metadata(
        parameters=CHILD_TENANT_PARAMS,
        entities=[HOSTNAME_ENTITY],
        integration_config_file_path=CONFIG_PATH,
    )
    def test_child_tenant_auth_when_action_cid_is_provided(
        self,
        script_session: CrowdStrikeFalconSession,
        action_output: MockActionOutput,
    ) -> None:
        """Tests that the action's Customer ID targets a child tenant."""
        ListHostVulnerabilities.main()
        auth_request: Any = script_session.request_history[0]
        token_request_payload: dict[str, Any] = auth_request.request.kwargs.get(
            "data", {},
        )
        assert token_request_payload.get("member_cid") == ACTION_CUSTOMER_ID

        vulnerability_request = next(
            (record for record in script_session.request_history if
             record.request.url.path == "/spotlight/queries/vulnerabilities/v1"),
            None,
        )
        assert vulnerability_request is not None, "Vulnerability query not found"

        request_params = vulnerability_request.request.kwargs.get("params", {})
        filter_string = request_params.get("filter")
        assert f"cid: '{ACTION_CUSTOMER_ID}'" in filter_string

        assert action_output.results.execution_state == ExecutionState.COMPLETED

    @set_metadata(
        parameters=PARENT_TENANT_PARAMS,
        entities=[HOSTNAME_ENTITY],
        integration_config=INTEGRATION_CONFIG_WITH_CID,
    )
    def test_child_tenant_auth_falls_back_to_integration_cid(
        self,
        script_session: CrowdStrikeFalconSession,
        action_output: MockActionOutput,
    ) -> None:
        """Tests fallback to the integration's CID when the action's is empty."""
        ListHostVulnerabilities.main()
        auth_request: Any = script_session.request_history[0]
        token_request_payload: dict[str, Any] = auth_request.request.kwargs.get(
            "data", {},
        )
        assert token_request_payload.get("member_cid") == INTEGRATION_CUSTOMER_ID

        vulnerability_request = next(
            (record for record in script_session.request_history if
             record.request.url.path == "/spotlight/queries/vulnerabilities/v1"),
            None,
        )
        assert vulnerability_request is not None, "Vulnerability query not found"

        request_params = vulnerability_request.request.kwargs.get("params", {})
        filter_string = request_params.get("filter")
        assert f"cid: '{INTEGRATION_CUSTOMER_ID}'" in filter_string

        assert action_output.results.execution_state == ExecutionState.COMPLETED

    @set_metadata(
        parameters=CHILD_TENANT_PARAMS,
        entities=[HOSTNAME_ENTITY],
        integration_config=INTEGRATION_CONFIG_WITH_CID,
    )
    def test_action_cid_overrides_integration_cid(
        self,
        script_session: CrowdStrikeFalconSession,
        action_output: MockActionOutput,
    ) -> None:
        """Tests that the action's Customer ID overrides the integration's CID."""
        ListHostVulnerabilities.main()
        auth_request: Any = script_session.request_history[0]
        token_request_payload: dict[str, Any] = auth_request.request.kwargs.get(
            "data", {},
        )
        assert token_request_payload.get("member_cid") == ACTION_CUSTOMER_ID

        vulnerability_request = next(
            (record for record in script_session.request_history if
             record.request.url.path == "/spotlight/queries/vulnerabilities/v1"),
            None,
        )
        assert vulnerability_request is not None, "Vulnerability query not found"

        request_params = vulnerability_request.request.kwargs.get("params", {})
        filter_string = request_params.get("filter")
        assert f"cid: '{ACTION_CUSTOMER_ID}'" in filter_string

        assert action_output.results.execution_state == ExecutionState.COMPLETED
