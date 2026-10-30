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

"""Unit tests for the CrowdStrikeFalcon Get Host Information action."""
from __future__ import annotations

import datetime
from typing import Any
from copy import deepcopy
from unittest.mock import patch

import pytest
from integration_testing.request import HttpMethod, MockRequest
from integration_testing.requests.response import MockResponse
from crowd_strike_falcon.actions import GetHostInformation
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
WRONG_ENTITY: Entity = create_entity(WRONG_ENTITY_ID, EntityTypesEnum.FILE_NAME)

CREATE_INSIGHT: bool = True
PARAMS: SingleJson = {"Customer ID": "", "Create Insight": CREATE_INSIGHT}
SUCCESS_OUTPUT_MESSAGE: str = (
    "Successfully enriched the following entities using Crowdstrike Falcon: "
    f"{HOSTNAME_ENTITY_ID}"
    "\n"
)
FAILURE_OUTPUT_MESSAGE: str = "No entities were enriched."

ACTION_CUSTOMER_ID: str = "action_cid_123"
INTEGRATION_CUSTOMER_ID: str = "integration_cid_456"

BASE_PARAMS: SingleJson = {
    "Create Insight": CREATE_INSIGHT,
}
PARENT_TENANT_PARAMS: SingleJson = {**BASE_PARAMS, "Customer ID": ""}
CHILD_TENANT_PARAMS: SingleJson = {
    **BASE_PARAMS, "Customer ID": ACTION_CUSTOMER_ID,
}
DEVICE_ID_PARAMS: SingleJson = {
    **BASE_PARAMS,
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

SCRIPT_DEADLINE_TIME: datetime.datetime = (
    datetime.datetime.now() + datetime.timedelta(minutes=10)
)
TIMEOUT_CONTEXT: SingleJson = {
    "execution_deadline_unix_time_ms": int(
        SCRIPT_DEADLINE_TIME.timestamp() * 1000,
    ),
}


@pytest.fixture
def setup_test_data(crowd_strike_falcon: CrowdStrikeFalcon) -> None:
    """Prepare mock data for tests."""
    crowd_strike_falcon.add_device(MOCK_DATA["get_devices"]["resources"][0])
    crowd_strike_falcon.add_login_history(
        MOCK_DATA["get_device_combine"]["resources"][0],
    )
    crowd_strike_falcon.add_online_state(
        MOCK_DATA["get_devices_entities_online_state"]["resources"][0],
    )


@pytest.mark.usefixtures("script_session")
class TestHappyPath:
    """Tests for the action's happy paths."""

    @set_metadata(
        parameters=DEVICE_ID_PARAMS,
        entities=[],
        integration_config_file_path=CONFIG_PATH,
    )
    @pytest.mark.usefixtures("setup_test_data")
    def test_get_host_information_with_device_id_success(
        self,
        action_output: MockActionOutput,
    ) -> None:
        """Tests a successful run of getting host information with device ID."""
        GetHostInformation.main()

        assert action_output.results.output_message == "Successfully enriched the following entities using Crowdstrike Falcon: 2a1c5ef609ac479ba77f8ca5879c82fc\n"
        assert action_output.results.result_value is True
        assert action_output.results.execution_state == ExecutionState.COMPLETED

    @set_metadata(
        parameters=PARAMS,
        entities=[HOSTNAME_ENTITY],
        integration_config_file_path=CONFIG_PATH,
    )
    @pytest.mark.usefixtures("setup_test_data")
    def test_get_host_information_success(
        self,
        script_session: CrowdStrikeFalconSession,
        action_output: MockActionOutput,
    ) -> None:
        """Tests a successful run of getting host information."""
        GetHostInformation.main()

        assert len(script_session.request_history) >= 4
        assert action_output.results.output_message == SUCCESS_OUTPUT_MESSAGE
        assert action_output.results.result_value is True
        assert action_output.results.execution_state == ExecutionState.COMPLETED

    @set_metadata(
        parameters=PARAMS,
        entities=[HOSTNAME_ENTITY],
        integration_config_file_path=CONFIG_PATH,
    )
    @patch("crowd_strike_falcon.core.CrowdStrikeManager.PAGE_SIZE", 2)
    def test_get_host_information_success_multiple_pages(
        self,
        script_session: CrowdStrikeFalconSession,
        action_output: MockActionOutput,
        crowd_strike_falcon: CrowdStrikeFalcon,
    ) -> None:
        """Tests getting host information when pagination is needed (multiple pages)."""
        # Register 3 devices in the mock server
        device_1 = deepcopy(MOCK_DATA["get_devices"]["resources"][0])
        device_1["device_id"] = "id_1"
        device_1["cid"] = "mock_valid"
        crowd_strike_falcon.add_device(device_1)

        device_2 = deepcopy(device_1)
        device_2["device_id"] = "id_2"
        crowd_strike_falcon.add_device(device_2)

        device_3 = deepcopy(device_1)
        device_3["device_id"] = "id_3"
        crowd_strike_falcon.add_device(device_3)

        # Register login history and online state
        login_1 = deepcopy(MOCK_DATA["get_device_combine"]["resources"][0])
        login_1["device_id"] = "id_1"
        crowd_strike_falcon.add_login_history(login_1)
        login_2 = deepcopy(login_1)
        login_2["device_id"] = "id_2"
        crowd_strike_falcon.add_login_history(login_2)
        login_3 = deepcopy(login_1)
        login_3["device_id"] = "id_3"
        crowd_strike_falcon.add_login_history(login_3)

        online_1 = deepcopy(MOCK_DATA["get_devices_entities_online_state"]["resources"][0])
        online_1["id"] = "id_1"
        crowd_strike_falcon.add_online_state(online_1)
        online_2 = deepcopy(online_1)
        online_2["id"] = "id_2"
        crowd_strike_falcon.add_online_state(online_2)
        online_3 = deepcopy(online_1)
        online_3["id"] = "id_3"
        crowd_strike_falcon.add_online_state(online_3)

        # Mock the search endpoint to return paginated lists of IDs
        def mock_search_devices_ids(request: MockRequest) -> MockResponse:
            params = request.kwargs.get("params", {})
            offset = int(params.get("offset", 0) or 0)

            if offset == 0:
                resources = ["id_1", "id_2"]
            else:
                resources = ["id_3"]

            return MockResponse(
                content={
                    "meta": {
                        "pagination": {
                            "offset": offset,
                            "limit": 2,
                            "total": 3
                        }
                    },
                    "resources": resources,
                    "errors": []
                },
                status_code=200
            )

        # Patch the router function on script_session
        script_session.routes[HttpMethod.GET.value]["/devices/queries/devices/v1"] = mock_search_devices_ids

        # Run the action
        GetHostInformation.main()

        # Check results
        assert action_output.results.output_message == SUCCESS_OUTPUT_MESSAGE
        assert action_output.results.result_value is True
        assert action_output.results.execution_state == ExecutionState.COMPLETED

    @set_metadata(
        parameters=PARAMS,
        entities=[HOSTNAME_ENTITY],
        integration_config_file_path=CONFIG_PATH,
    )
    def test_get_host_information_success_large_data(
        self,
        script_session: CrowdStrikeFalconSession,
        action_output: MockActionOutput,
        crowd_strike_falcon: CrowdStrikeFalcon,
    ) -> None:
        """Tests successful run of getting host information with more than 100 matching devices."""
        total_devices = 500
        # Register 500 devices in the mock server
        for i in range(total_devices):
            device_id = f"id_{i}"

            device = deepcopy(MOCK_DATA["get_devices"]["resources"][0])
            device["device_id"] = device_id
            device["cid"] = "mock_valid"
            crowd_strike_falcon.add_device(device)

            login = deepcopy(MOCK_DATA["get_device_combine"]["resources"][0])
            login["device_id"] = device_id
            crowd_strike_falcon.add_login_history(login)

            online = deepcopy(MOCK_DATA["get_devices_entities_online_state"]["resources"][0])
            online["id"] = device_id
            crowd_strike_falcon.add_online_state(online)

        # Mock the search endpoint to return 500 IDs
        def mock_search_devices_ids(request: MockRequest) -> MockResponse:
            return MockResponse(
                content={
                    "meta": {
                        "pagination": {
                            "offset": 0,
                            "limit": total_devices,
                            "total": total_devices
                        }
                    },
                    "resources": [f"id_{i}" for i in range(total_devices)],
                    "errors": []
                },
                status_code=200
            )

        # Mock the details endpoint to return only the requested IDs (to test chunking)
        def mock_get_devices(request: MockRequest) -> MockResponse:
            params = request.kwargs.get("params", {})
            ids = params.get("ids", [])
            if isinstance(ids, str):
                ids = [ids]
            parsed_ids = []
            for item in ids:
                if item.startswith("[") and item.endswith("]"):
                    import ast
                    parsed_ids.extend(ast.literal_eval(item))
                else:
                    parsed_ids.append(item)

            resources = []
            for device_id in parsed_ids:
                if device_id in crowd_strike_falcon._devices:
                    resources.append(crowd_strike_falcon.get_device(device_id).to_json())

            return MockResponse(
                content={"resources": resources, "errors": []},
                status_code=200
            )

        script_session.routes[HttpMethod.GET.value]["/devices/queries/devices/v1"] = mock_search_devices_ids
        script_session.routes[HttpMethod.GET.value]["/devices/entities/devices/v2"] = mock_get_devices

        GetHostInformation.main()

        assert action_output.results.output_message == SUCCESS_OUTPUT_MESSAGE
        assert action_output.results.result_value is True
        assert action_output.results.execution_state == ExecutionState.COMPLETED

        entities_calls = [
            req for req in script_session.request_history
            if req.request.real_url == "/devices/entities/devices/v2"
        ]
        assert len(entities_calls) == 5

    @set_metadata(
        parameters=PARAMS,
        entities=[WRONG_ENTITY],
        integration_config_file_path=CONFIG_PATH,
    )
    def test_get_host_information_wrong_entity(
        self,
        script_session: CrowdStrikeFalconSession,
        action_output: MockActionOutput,
    ) -> None:
        """Tests the action's behavior with an unsupported entity type."""
        GetHostInformation.main()

        assert len(script_session.request_history) == 1
        assert action_output.results.output_message == FAILURE_OUTPUT_MESSAGE
        assert action_output.results.result_value is False
        assert action_output.results.execution_state == ExecutionState.COMPLETED


@pytest.mark.usefixtures("script_session", "setup_test_data")
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
        GetHostInformation.main()
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
        GetHostInformation.main()
        history_record: Any = script_session.request_history[0]
        token_request_payload: dict[str, Any] = history_record.request.kwargs.get(
            "data", {},
        )
        assert token_request_payload.get("member_cid") == ACTION_CUSTOMER_ID
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
        GetHostInformation.main()
        history_record: Any = script_session.request_history[0]
        token_request_payload: dict[str, Any] = history_record.request.kwargs.get(
            "data", {},
        )
        assert token_request_payload.get("member_cid") == INTEGRATION_CUSTOMER_ID
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
        GetHostInformation.main()

        auth_request: Any = script_session.request_history[0]
        token_request_payload: dict[str, Any] = auth_request.request.kwargs.get(
            "data", {},
        )
        assert token_request_payload.get("member_cid") == ACTION_CUSTOMER_ID
        assert action_output.results.execution_state == ExecutionState.COMPLETED

        device_search_request = next(
            (record for record in script_session.request_history
             if record.request.url.path == "/devices/queries/devices/v1"),
            None,
        )
        assert (
            device_search_request is not None
        ), "API call to search devices was not found"

        request_params = device_search_request.request.kwargs.get("params", {})
        filter_string = request_params.get("filter")
        assert filter_string, "Filter string should not be empty"

        actual_filters = {
            key.strip(): val.strip()
            for key, val in (part.split(":", 1) for part in filter_string.split("+"))
        }

        error_msg = "The 'cid' key was not found in the filter parameters."
        assert "cid" in actual_filters, error_msg
        assert actual_filters["cid"] == f"'{ACTION_CUSTOMER_ID}'"

        login_history_request = next(
            (record for record in script_session.request_history
             if record.request.url.path ==
             "/devices/combined/devices/login-history/v1"),
            None,
        )
        assert (
            login_history_request is not None
        ), "API call to get login history was not found"

        request_headers = login_history_request.request.kwargs.get("headers", {})
        error_msg = "CID Header not found in login history request"
        assert "X-CS-CUSTID" in request_headers, error_msg
        assert request_headers["X-CS-CUSTID"] == ACTION_CUSTOMER_ID
