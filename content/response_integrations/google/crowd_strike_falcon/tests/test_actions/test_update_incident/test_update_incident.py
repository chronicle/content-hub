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

"""Unit tests for the CrowdStrikeFalcon Update Incident action."""
from __future__ import annotations

from typing import Any

import pytest
from crowd_strike_falcon.actions import UpdateIncident
from TIPCommon.base.action import ExecutionState
from TIPCommon.types import SingleJson

from crowd_strike_falcon.tests.common import CONFIG_PATH, MOCK_DATA
from crowd_strike_falcon.tests.core.crowd_strike_falcon import CrowdStrikeFalcon
from crowd_strike_falcon.tests.core.session import CrowdStrikeFalconSession
from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata

INCIDENT_ID: str = (
    "inc:d498fc988cd34ab3b946b46cff08d88a:52c4e39e284a4035b1177c780be39df8"
)
WRONG_INCIDENT_ID: str = "no_ids"
ASSIGN_TO_USER: str = "test@example.com"
STATUS_VALUE: str = "Closed"
SUCCESS_PARAM: SingleJson = {
    "Customer ID": "",
    "Incident ID": INCIDENT_ID,
    "Status": STATUS_VALUE,
    "Assign to": "",
}
FAILURE_PARAM: SingleJson = {
    "Customer ID": "",
    "Incident ID": WRONG_INCIDENT_ID,
    "Status": STATUS_VALUE,
    "Assign to": "",
}
SUCCESS_OUTPUT_MESSAGE: str = (
    f"Successfully updated incident with ID {INCIDENT_ID} in Crowdstrike"
)
FAILURE_OUTPUT_MESSAGE: str = (
    "Error executing action CrowdStrikeFalcon - Update Incident. Reason: Incident "
    f"with ID {WRONG_INCIDENT_ID} wasn't found in Crowdstrike. "
    "Please check the spelling: invalid element in the request"
)

# Constants for Customer ID tests
ACTION_CUSTOMER_ID: str = "action_cid_123"
INTEGRATION_CUSTOMER_ID: str = "integration_cid_456"

BASE_PARAMS: SingleJson = {
    "Incident ID": INCIDENT_ID,
    "Status": STATUS_VALUE,
    "Assign to": ASSIGN_TO_USER,
}

PARENT_TENANT_PARAMS: SingleJson = {**BASE_PARAMS, "Customer ID": ""}
CHILD_TENANT_PARAMS: SingleJson = {**BASE_PARAMS, "Customer ID": ACTION_CUSTOMER_ID}

INTEGRATION_CONFIG_WITH_CID: SingleJson = {
    "API Root": "https://api.crowdstrike.com",
    "Client API ID": "dummy",
    "Client API Secret": "dummy",
    "Verify SSL": "False",
    "Customer ID": INTEGRATION_CUSTOMER_ID,
}


@pytest.fixture
def setup_crowdstrike_data(crowd_strike_falcon: CrowdStrikeFalcon) -> None:
    """Prepares mock data for tests."""
    crowd_strike_falcon.add_entries(
        "incidents",
        MOCK_DATA["get_incidents_details"]["resources"],
    )


@pytest.mark.usefixtures("script_session")
class TestHappyPath:
    """Tests for the action's happy paths."""

    @set_metadata(
        parameters=SUCCESS_PARAM,
        integration_config_file_path=CONFIG_PATH,
    )
    def test_update_incident_success(
        self,
        script_session: CrowdStrikeFalconSession,
        crowd_strike_falcon: CrowdStrikeFalcon,
        action_output: MockActionOutput,
    ) -> None:
        crowd_strike_falcon.add_entries(
            "incidents",
            MOCK_DATA["get_incidents_details"]["resources"],
        )

        UpdateIncident.main()

        assert len(script_session.request_history) == 4
        assert action_output.results.output_message == SUCCESS_OUTPUT_MESSAGE
        assert action_output.results.result_value is True
        assert action_output.results.execution_state == ExecutionState.COMPLETED

    @set_metadata(
        parameters=FAILURE_PARAM,
        integration_config_file_path=CONFIG_PATH,
    )
    def test_update_incident_wrong_id(
        self,
        script_session: CrowdStrikeFalconSession,
        action_output: MockActionOutput,
    ) -> None:
        UpdateIncident.main()

        assert len(script_session.request_history) == 2
        assert action_output.results.output_message == FAILURE_OUTPUT_MESSAGE
        assert action_output.results.execution_state == ExecutionState.FAILED


@pytest.mark.usefixtures("script_session", "setup_crowdstrike_data")
class TestMemberCID:
    """Tests for Customer ID (member_cid) functionality."""

    @set_metadata(
        parameters=PARENT_TENANT_PARAMS,
        integration_config_file_path=CONFIG_PATH,
    )
    def test_parent_tenant_auth_when_no_cid_is_provided(
        self,
        script_session: CrowdStrikeFalconSession,
        action_output: MockActionOutput,
    ) -> None:
        """Tests that auth targets the parent tenant when no Customer ID is given."""
        UpdateIncident.main()
        history_record: Any = script_session.request_history[0]
        token_request_payload: dict[str, Any] = history_record.request.kwargs.get(
            "data", {},
        )
        assert "member_cid" not in token_request_payload
        assert action_output.results.execution_state == ExecutionState.COMPLETED

    @set_metadata(
        parameters=CHILD_TENANT_PARAMS,
        integration_config_file_path=CONFIG_PATH,
    )
    def test_child_tenant_auth_when_action_cid_is_provided(
        self,
        script_session: CrowdStrikeFalconSession,
        action_output: MockActionOutput,
    ) -> None:
        """Tests that the action's Customer ID targets a child tenant."""
        UpdateIncident.main()
        auth_request: Any = script_session.request_history[0]
        token_request_payload: dict[str, Any] = auth_request.request.kwargs.get(
            "data", {},
        )
        assert token_request_payload.get("member_cid") == ACTION_CUSTOMER_ID

        user_search_request = next(
            r for r in script_session.request_history
            if r.request.url.path == "/user-management/queries/users/v1"
        )
        filter_string = user_search_request.request.kwargs.get("params", {}).get(
            "filter",
        )
        assert f"+cid:'{ACTION_CUSTOMER_ID}'" in filter_string

        assert action_output.results.execution_state == ExecutionState.COMPLETED

    @set_metadata(
        parameters=PARENT_TENANT_PARAMS,
        integration_config=INTEGRATION_CONFIG_WITH_CID,
    )
    def test_child_tenant_auth_falls_back_to_integration_cid(
        self,
        script_session: CrowdStrikeFalconSession,
        action_output: MockActionOutput,
    ) -> None:
        """Tests fallback to the integration's CID when the action's is empty."""
        UpdateIncident.main()
        auth_request: Any = script_session.request_history[0]
        token_request_payload: dict[str, Any] = auth_request.request.kwargs.get(
            "data", {},
        )
        assert token_request_payload.get("member_cid") == INTEGRATION_CUSTOMER_ID

        user_search_request = next(
            r for r in script_session.request_history
            if r.request.url.path == "/user-management/queries/users/v1"
        )
        filter_string = user_search_request.request.kwargs.get("params", {}).get(
            "filter",
        )
        assert f"+cid:'{INTEGRATION_CUSTOMER_ID}'" in filter_string

        assert action_output.results.execution_state == ExecutionState.COMPLETED

    @set_metadata(
        parameters=CHILD_TENANT_PARAMS,
        integration_config=INTEGRATION_CONFIG_WITH_CID,
    )
    def test_action_cid_overrides_integration_cid(
        self,
        script_session: CrowdStrikeFalconSession,
        action_output: MockActionOutput,
    ) -> None:
        """Tests that the action's Customer ID overrides the integration's CID."""
        UpdateIncident.main()
        auth_request: Any = script_session.request_history[0]
        token_request_payload: dict[str, Any] = auth_request.request.kwargs.get(
            "data", {},
        )
        assert token_request_payload.get("member_cid") == ACTION_CUSTOMER_ID

        user_search_request = next(
            r for r in script_session.request_history
            if r.request.url.path == "/user-management/queries/users/v1"
        )
        filter_string = user_search_request.request.kwargs.get("params", {}).get(
            "filter",
        )
        assert f"+cid:'{ACTION_CUSTOMER_ID}'" in filter_string

        assert action_output.results.execution_state == ExecutionState.COMPLETED
