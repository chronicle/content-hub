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

"""Unit tests for the CrowdStrikeFalcon Execute Command action."""
from __future__ import annotations

import copy
import datetime
from typing import Any

import pytest
from crowd_strike_falcon.actions import ExecuteCommand
from TIPCommon.base.action import ExecutionState
from TIPCommon.types import SingleJson

from crowd_strike_falcon.tests.common import (
    CONFIG_PATH,
    HOSTNAME_ENTITY,
    HOSTNAME_ENTITY_ID,
    MOCK_DATA,
)
from crowd_strike_falcon.tests.core.crowd_strike_falcon import CrowdStrikeFalcon
from crowd_strike_falcon.tests.core.session import CrowdStrikeFalconSession
from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata

OVERWRITE: bool = False
COMMAND: str = "ls"
SUCCESS_OUTPUT_MESSAGE: str = (
    f"Successfully executed command '{COMMAND}' on the following endpoints in "
    f"Crowdstrike Falcon: {HOSTNAME_ENTITY_ID}"
    "\n"
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
    "Overwrite": OVERWRITE,
    "Command": COMMAND,
    "Hostname": "",
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


@pytest.fixture
def setup_crowdstrike_data(crowd_strike_falcon: CrowdStrikeFalcon) -> None:
    """Prepare mock data for tests."""
    crowd_strike_falcon.add_device(MOCK_DATA["get_devices"]["resources"][1])
    crowd_strike_falcon.add_online_state(
        MOCK_DATA["get_devices_entities_online_state"]["resources"][0],
    )


@pytest.mark.usefixtures("script_session")
class TestHappyPath:
    """Tests for the action's successful execution paths."""

    @set_metadata(
        parameters=DEVICE_ID_PARAMS,
        entities=[],
        integration_config_file_path=CONFIG_PATH,
        input_context=copy.deepcopy(TIMEOUT),
    )
    @pytest.mark.usefixtures("setup_crowdstrike_data")
    def test_execute_command_with_device_id_success(
        self,
        action_output: MockActionOutput,
    ) -> None:
        """Tests a successful run of executing a command with device ID."""
        ExecuteCommand.main(True)

        assert action_output.results.output_message == "Successfully executed command 'ls' on the following endpoints in Crowdstrike Falcon: 2a1c5ef609ac479ba77f8ca5879c82fc\n"
        assert action_output.results.result_value is True
        assert action_output.results.execution_state == ExecutionState.COMPLETED

    @set_metadata(
        parameters={
            "Customer ID": "",
            "Overwrite": OVERWRITE,
            "Command": COMMAND,
        },
        entities=[HOSTNAME_ENTITY],
        integration_config_file_path=CONFIG_PATH,
        input_context=copy.deepcopy(TIMEOUT),
    )
    @pytest.mark.usefixtures("setup_crowdstrike_data")
    def test_execute_command_success(
        self,
        script_session: CrowdStrikeFalconSession,
        action_output: MockActionOutput,
    ) -> None:
        """Tests a successful run of executing a command."""
        ExecuteCommand.main(True)

        assert len(script_session.request_history) == 8
        assert action_output.results.output_message == SUCCESS_OUTPUT_MESSAGE
        assert action_output.results.result_value is True
        assert action_output.results.execution_state == ExecutionState.COMPLETED


@pytest.mark.usefixtures("script_session", "setup_crowdstrike_data")
class TestMemberCID:
    """Tests for multi-tenancy customer ID (CID) handling."""

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
        """Verifies authentication targets the parent tenant if no CID is given."""
        ExecuteCommand.main(True)
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
        """Verifies auth uses the action's CID when provided."""
        ExecuteCommand.main(True)
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
        input_context=copy.deepcopy(TIMEOUT),
    )
    def test_child_tenant_auth_falls_back_to_integration_cid(
        self,
        script_session: CrowdStrikeFalconSession,
        action_output: MockActionOutput,
    ) -> None:
        """Verifies auth uses the integration's CID if the action's is empty."""
        ExecuteCommand.main(True)
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
        input_context=copy.deepcopy(TIMEOUT),
    )
    def test_action_cid_overrides_integration_cid(
        self,
        script_session: CrowdStrikeFalconSession,
        action_output: MockActionOutput,
    ) -> None:
        """Verifies that the action's CID takes precedence over the integration's."""
        ExecuteCommand.main(True)

        auth_request: Any = script_session.request_history[0]
        token_request_payload: dict[str, Any] = auth_request.request.kwargs.get(
            "data", {},
        )
        assert token_request_payload.get("member_cid") == ACTION_CUSTOMER_ID
        assert action_output.results.execution_state == ExecutionState.COMPLETED

        all_device_searches = [
            r
            for r in script_session.request_history
            if r.request.url.path == "/devices/queries/devices/v1"
        ]
        assert len(
            all_device_searches,
        ) >= 2, "Expected at least two device search API calls"
        device_search_request = all_device_searches[1]

        request_params = device_search_request.request.kwargs.get("params", {})
        assert (
            "filter" in request_params
        ), "Filter parameter is missing in the device search query"

        filter_string = request_params.get("filter")
        assert filter_string, "Filter string should not be empty"

        actual_filters = {
            key.strip(): val.strip()
            for key, val in (part.split(":", 1) for part in filter_string.split("+"))
        }

        error_msg = "The 'cid' key was not found in the filter parameters."
        assert "cid" in actual_filters, error_msg
        assert actual_filters["cid"] == f"'{ACTION_CUSTOMER_ID}'"
