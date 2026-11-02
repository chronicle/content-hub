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

"""Unit tests for the CrowdStrikeFalcon Run Script action."""
from __future__ import annotations

import copy
import datetime
from typing import Any

import pytest
from crowd_strike_falcon.actions import RunScript
from TIPCommon.base.action import ExecutionState
from TIPCommon.types import SingleJson

from crowd_strike_falcon.tests.common import (
    CONFIG_PATH,
    HOSTNAME_ENTITY,
    MOCK_DATA,
)
from crowd_strike_falcon.tests.core.crowd_strike_falcon import CrowdStrikeFalcon
from crowd_strike_falcon.tests.core.session import CrowdStrikeFalconSession
from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata

RUN_SCRIPT: str = "ls"

SUCCESS_OUTPUT_MESSAGE: str = (
    "Script wasn't executed on the provided endpoints in CrowdStrikeFalcon."
)
SCRIPT_DEADLINE_TIME: datetime.datetime = (
    datetime.datetime.now() + datetime.timedelta(minutes=10)
)
TIMEOUT: SingleJson = {
    "execution_deadline_unix_time_ms": int(
        SCRIPT_DEADLINE_TIME.timestamp() * 1000,
    ),
}

ACTION_CUSTOMER_ID: str = "action_cid_123"
INTEGRATION_CUSTOMER_ID: str = "integration_cid_456"

BASE_PARAMS: SingleJson = {
    "Script Name": "",
    "Raw Script": RUN_SCRIPT,
    "Hostname": "",
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


@pytest.fixture
def setup_crowdstrike_data(crowd_strike_falcon: CrowdStrikeFalcon) -> None:
    """Prepares mock data for tests by adding a single unique device."""
    crowd_strike_falcon.add_device(
        MOCK_DATA["get_devices"]["resources"][0],
    )
    crowd_strike_falcon.add_entries(
        "online_states",
        MOCK_DATA["get_devices_entities_online_state"]["resources"],
    )


@pytest.mark.usefixtures("script_session")
class TestHappyPath:
    """Tests for the action's happy paths."""

    @set_metadata(
        parameters={
            "Customer ID": "",
            "Script Name": "",
            "Raw Script": RUN_SCRIPT,
        },
        entities=[HOSTNAME_ENTITY],
        integration_config_file_path=CONFIG_PATH,
        input_context=copy.deepcopy(TIMEOUT),
    )
    def test_run_script_success(
        self,
        script_session: CrowdStrikeFalconSession,
        crowd_strike_falcon: CrowdStrikeFalcon,
        action_output: MockActionOutput,
    ) -> None:
        crowd_strike_falcon.add_entries(
            "devices",
            MOCK_DATA["get_devices_entities_online_state"]["resources"],
        )

        RunScript.main()

        assert len(script_session.request_history) == 4
        assert action_output.results.output_message == SUCCESS_OUTPUT_MESSAGE
        assert action_output.results.result_value is False
        assert action_output.results.execution_state == ExecutionState.COMPLETED

    @set_metadata(
        parameters={
            "Customer ID": "",
            "Script Name": "",
            "Raw Script": RUN_SCRIPT,
            "Device ID": "2a1c5ef609ac479ba77f8ca5879c82fc",
        },
        entities=[],
        integration_config_file_path=CONFIG_PATH,
        input_context=copy.deepcopy(TIMEOUT),
    )
    def test_run_script_with_device_id_success(
        self,
        script_session: CrowdStrikeFalconSession,
        crowd_strike_falcon: CrowdStrikeFalcon,
        action_output: MockActionOutput,
    ) -> None:
        crowd_strike_falcon.add_entries(
            "devices",
            MOCK_DATA["get_devices_entities_online_state"]["resources"],
        )

        RunScript.main()

        assert action_output.results.output_message == SUCCESS_OUTPUT_MESSAGE
        assert action_output.results.result_value is False
        assert action_output.results.execution_state == ExecutionState.COMPLETED


@pytest.mark.usefixtures("script_session", "setup_crowdstrike_data")
class TestMemberCID:
    """Tests for Customer ID (member_cid) functionality."""

    @set_metadata(
        parameters=PARENT_TENANT_PARAMS,
        entities=[HOSTNAME_ENTITY],
        integration_config_file_path=CONFIG_PATH,
        input_context=copy.deepcopy(TIMEOUT),
    )
    def test_parent_tenant_auth_when_no_cid_is_provided(
        self,
        script_session: CrowdStrikeFalconSession,
        action_output: MockActionOutput,
    ) -> None:
        """Tests that auth targets the parent tenant when no Customer ID is given."""
        RunScript.main()
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
        input_context=copy.deepcopy(TIMEOUT),
    )
    def test_child_tenant_auth_when_action_cid_is_provided(
        self,
        script_session: CrowdStrikeFalconSession,
        action_output: MockActionOutput,
    ) -> None:
        """Tests that the action's Customer ID targets a child tenant."""
        RunScript.main()
        auth_request: Any = script_session.request_history[0]
        token_request_payload: dict[str, Any] = auth_request.request.kwargs.get(
            "data", {},
        )
        assert token_request_payload.get("member_cid") == ACTION_CUSTOMER_ID

        device_search_request = next(
            record for record in script_session.request_history
            if record.request.url.path == "/devices/queries/devices/v1"
        )
        request_params = device_search_request.request.kwargs.get("params", {})
        filter_string = request_params.get("filter")
        assert f"cid: '{ACTION_CUSTOMER_ID}'" in filter_string

        assert action_output.results.execution_state == ExecutionState.COMPLETED

    @set_metadata(
        parameters=PARENT_TENANT_PARAMS,
        entities=[HOSTNAME_ENTITY],
        integration_config=INTEGRATION_CONFIG_WITH_CID,
        input_context=copy.deepcopy(TIMEOUT),
    )
    def test_child_tenant_auth_falls_back_to_integration_cid(
        self,
        script_session: CrowdStrikeFalconSession,
        action_output: MockActionOutput,
    ) -> None:
        """Tests fallback to the integration's CID when the action's is empty."""
        RunScript.main()
        auth_request: Any = script_session.request_history[0]
        token_request_payload: dict[str, Any] = auth_request.request.kwargs.get(
            "data", {},
        )
        assert token_request_payload.get("member_cid") == INTEGRATION_CUSTOMER_ID

        device_search_request = next(
            record for record in script_session.request_history
            if record.request.url.path == "/devices/queries/devices/v1"
        )
        request_params = device_search_request.request.kwargs.get("params", {})
        filter_string = request_params.get("filter")
        assert f"cid: '{INTEGRATION_CUSTOMER_ID}'" in filter_string

        assert action_output.results.execution_state == ExecutionState.COMPLETED

    @set_metadata(
        parameters=CHILD_TENANT_PARAMS,
        entities=[HOSTNAME_ENTITY],
        integration_config=INTEGRATION_CONFIG_WITH_CID,
        input_context=copy.deepcopy(TIMEOUT),
    )
    def test_action_cid_overrides_integration_cid(
        self,
        script_session: CrowdStrikeFalconSession,
        action_output: MockActionOutput,
    ) -> None:
        """Tests that the action's Customer ID overrides the integration's CID."""
        RunScript.main()
        auth_request: Any = script_session.request_history[0]
        token_request_payload: dict[str, Any] = auth_request.request.kwargs.get(
            "data", {},
        )
        assert token_request_payload.get("member_cid") == ACTION_CUSTOMER_ID

        device_search_request = next(
            record for record in script_session.request_history
            if record.request.url.path == "/devices/queries/devices/v1"
        )

        request_params = device_search_request.request.kwargs.get("params", {})
        assert "filter" in request_params, "Filter parameter is missing"

        filter_string = request_params.get("filter")
        assert filter_string, "Filter string should not be empty"

        actual_filters = {
            key.strip(): val.strip()
            for key, val in (part.split(":", 1) for part in filter_string.split("+"))
        }

        error_msg = "The 'cid' key was not found in the filter parameters."
        assert "cid" in actual_filters, error_msg
        assert actual_filters["cid"] == f"'{ACTION_CUSTOMER_ID}'"

        assert action_output.results.execution_state == ExecutionState.COMPLETED
