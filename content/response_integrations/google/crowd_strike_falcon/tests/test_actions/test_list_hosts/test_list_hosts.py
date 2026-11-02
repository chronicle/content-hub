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

"""Unit tests for the CrowdStrikeFalcon List Hosts action."""
from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest
from crowd_strike_falcon.actions import ListHosts
from TIPCommon.base.action import ExecutionState
from TIPCommon.types import SingleJson

from crowd_strike_falcon.tests.common import CONFIG_PATH, MOCK_DATA
from crowd_strike_falcon.tests.core.crowd_strike_falcon import CrowdStrikeFalcon
from crowd_strike_falcon.tests.core.session import CrowdStrikeFalconSession
from integration_testing.platform.script_output import MockActionOutput
from integration_testing.requests.response import MockResponse
from integration_testing.set_meta import set_metadata

ACTION_CUSTOMER_ID: str = "action_cid_123"
INTEGRATION_CUSTOMER_ID: str = "integration_cid_456"

BASE_PARAMS: SingleJson = {
    "Max Hosts To Return": 1,
    "Filter Value": "",
    "Filter Logic": "Equal",
}
PARENT_TENANT_PARAMS: SingleJson = {**BASE_PARAMS, "Customer ID": ""}
CHILD_TENANT_PARAMS: SingleJson = {
    **BASE_PARAMS, "Customer ID": ACTION_CUSTOMER_ID,
}

INTEGRATION_CONFIG_WITH_CID: SingleJson = {
    "API Root": "https://api.crowdstrike.com",
    "Client API ID": "dummy",
    "Client API Secret": "dummy",
    "Verify SSL": "False",
    "Customer ID": INTEGRATION_CUSTOMER_ID,
}

SUCCESS_OUTPUT_MESSAGE: str = (
    "Successfully retrieved available hosts based on the provided criteria."
)
FAILURE_OUTPUT_MESSAGE: str = "No hosts were found for the provided criteria."


@pytest.fixture
def setup_crowdstrike_data(crowd_strike_falcon: CrowdStrikeFalcon) -> None:
    """Prepare mock data with a single device for tests."""
    crowd_strike_falcon.add_device(MOCK_DATA["get_devices"]["resources"][0])


@pytest.mark.usefixtures("script_session")
class TestHappyPath:
    """Tests for the action's happy paths."""

    @set_metadata(
        parameters=CHILD_TENANT_PARAMS,
        integration_config_file_path=CONFIG_PATH,
    )
    @pytest.mark.usefixtures("setup_crowdstrike_data")
    def test_list_hosts_success(
        self,
        script_session: CrowdStrikeFalconSession,
        action_output: MockActionOutput,
    ) -> None:
        """Tests a successful run of listing hosts."""
        ListHosts.main()

        assert len(script_session.request_history) == 3
        assert action_output.results.output_message == SUCCESS_OUTPUT_MESSAGE
        assert action_output.results.result_value is True
        assert action_output.results.execution_state == ExecutionState.COMPLETED

        assert action_output.results.json_output.json_result

    @set_metadata(
        parameters={**CHILD_TENANT_PARAMS, "Filter Value": "non_existent_host"},
        integration_config_file_path=CONFIG_PATH,
    )
    def test_list_hosts_no_hosts_found(
        self,
        script_session: CrowdStrikeFalconSession,
        action_output: MockActionOutput,
    ) -> None:
        """Tests the case where no hosts match the criteria."""
        handler = MagicMock()
        handler.side_effect = [
            MockResponse(
                content={"resources": [], "meta": {"pagination": {"total": 0}}},
                status_code=200,
            ),
        ]
        script_session.routes["GET"]["/devices/queries/devices/v1"] = handler

        ListHosts.main()

        assert len(script_session.request_history) == 2
        assert action_output.results.output_message == FAILURE_OUTPUT_MESSAGE
        assert action_output.results.result_value is False
        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert action_output.results.json_output.json_result == []


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
        """Tests auth targets parent tenant when no Customer ID is given."""
        ListHosts.main()

        auth_request: Any = script_session.request_history[0]
        token_request_payload: dict[str, Any] = auth_request.request.kwargs.get(
            "data", {},
        )
        assert "member_cid" not in token_request_payload

        device_search_request: Any = script_session.request_history[1]
        request_params = device_search_request.request.kwargs.get("params", {})
        filter_string = request_params.get("filter")
        assert "cid:" not in filter_string

        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert action_output.results.result_value is True

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
        ListHosts.main()

        auth_request: Any = script_session.request_history[0]
        token_request_payload: dict[str, Any] = auth_request.request.kwargs.get(
            "data", {},
        )
        assert token_request_payload.get("member_cid") == ACTION_CUSTOMER_ID

        device_search_request: Any = script_session.request_history[1]
        request_params = device_search_request.request.kwargs.get("params", {})
        filter_string = request_params.get("filter")
        assert f"cid: '{ACTION_CUSTOMER_ID}'" in filter_string

        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert action_output.results.result_value is True

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
        ListHosts.main()

        auth_request: Any = script_session.request_history[0]
        token_request_payload: dict[str, Any] = auth_request.request.kwargs.get(
            "data", {},
        )
        assert token_request_payload.get("member_cid") == INTEGRATION_CUSTOMER_ID

        device_search_request: Any = script_session.request_history[1]
        request_params = device_search_request.request.kwargs.get("params", {})
        filter_string = request_params.get("filter")
        assert f"cid: '{INTEGRATION_CUSTOMER_ID}'" in filter_string

        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert action_output.results.result_value is True

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
        ListHosts.main()

        auth_request: Any = script_session.request_history[0]
        token_request_payload: dict[str, Any] = auth_request.request.kwargs.get(
            "data", {},
        )
        assert token_request_payload.get("member_cid") == ACTION_CUSTOMER_ID

        device_search_request: Any = script_session.request_history[1]
        request_params = device_search_request.request.kwargs.get("params", {})
        filter_string = request_params.get("filter")
        assert f"cid: '{ACTION_CUSTOMER_ID}'" in filter_string

        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert action_output.results.result_value is True
