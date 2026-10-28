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

"""Unit tests for the CrowdStrikeFalcon Lift Contained Endpoint action."""
from __future__ import annotations

import copy
import datetime
import json
from typing import Any

import pytest
from crowd_strike_falcon.actions import LiftContainedEndpoint
from TIPCommon.base.action import EntityTypesEnum, ExecutionState
from TIPCommon.types import Entity, SingleJson

from crowd_strike_falcon.tests.common import CONFIG_PATH, MOCK_DATA
from crowd_strike_falcon.tests.core.crowd_strike_falcon import CrowdStrikeFalcon
from crowd_strike_falcon.tests.core.session import CrowdStrikeFalconSession
from integration_testing.common import create_entity
from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata

HOSTNAME_ENTITY_ID: str = "npatni-sysopss"
HOSTNAME_ENTITY: Entity = create_entity(
    HOSTNAME_ENTITY_ID, EntityTypesEnum.HOST_NAME,
)

WRONG_ENTITY_ID: str = "wrong-entity"
WRONG_ENTITY: Entity = create_entity(WRONG_ENTITY_ID, EntityTypesEnum.FILE_NAME)

CUSTOMER_ID: str = "27fe4e476ca3490b8476b2b6650e5a741"
PARAMS: SingleJson = {"Customer ID": CUSTOMER_ID, "Fail If Timeout": False}

SUCCESS_OUTPUT_MESSAGE: str = (
    "The following endpoints were not contained in Crowdstrike Falcon: "
    f"{HOSTNAME_ENTITY_ID}\n"
)
FAILURE_OUTPUT_MESSAGE: str = (
    "None of the provided endpoints were found in Crowdstrike Falcon."
)

ACTION_CUSTOMER_ID: str = "action_cid_123"
INTEGRATION_CUSTOMER_ID: str = "integration_cid_456"

INTEGRATION_CONFIG_WITH_CID: SingleJson = {
    "API Root": "https://api.crowdstrike.com",
    "Client API ID": "dummy",
    "Client API Secret": "dummy",
    "Verify SSL": "False",
    "Customer ID": INTEGRATION_CUSTOMER_ID,
}
BASE_PARAMS: SingleJson = {"Fail If Timeout": False}
PARENT_TENANT_PARAMS: SingleJson = {**BASE_PARAMS, "Customer ID": ""}
CHILD_TENANT_PARAMS: SingleJson = {
    **BASE_PARAMS, "Customer ID": ACTION_CUSTOMER_ID,
}
DEVICE_ID_PARAMS: SingleJson = {
    **BASE_PARAMS,
    "Customer ID": "",
    "Device ID": "device_id_1",
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
def setup_device_data(crowd_strike_falcon: CrowdStrikeFalcon) -> None:
    """Prepare mock data with a findable device."""
    crowd_strike_falcon.add_device(
        copy.deepcopy(MOCK_DATA["get_devices"]["resources"][0]),
    )


@pytest.mark.usefixtures("script_session")
class TestHappyPath:
    """Tests for the action's successful execution paths."""

    @set_metadata(
        parameters=DEVICE_ID_PARAMS,
        entities=[],
        integration_config_file_path=CONFIG_PATH,
        input_context=copy.deepcopy(TIMEOUT_CONTEXT),
    )
    def test_list_contain_endpoint_with_device_id_success(
        self,
        crowd_strike_falcon: CrowdStrikeFalcon,
        action_output: MockActionOutput,
    ) -> None:
        """Verifies that the action correctly lifts containment from an endpoint using Device ID."""
        crowd_strike_falcon.add_device({
            "device_id": "device_id_1",
            "hostname": "device_id_1",
            "status": "normal",
        })

        LiftContainedEndpoint.main(True)

        assert action_output.results.output_message == "The following endpoints were not contained in Crowdstrike Falcon: device_id_1\n"
        assert action_output.results.result_value is True
        assert action_output.results.execution_state == ExecutionState.COMPLETED

    @set_metadata(
        parameters=PARAMS,
        entities=[HOSTNAME_ENTITY],
        integration_config_file_path=CONFIG_PATH,
        input_context=copy.deepcopy(TIMEOUT_CONTEXT),
    )
    def test_list_contain_endpoint_case(
        self,
        script_session: CrowdStrikeFalconSession,
        crowd_strike_falcon: CrowdStrikeFalcon,
        action_output: MockActionOutput,
    ) -> None:
        """Verifies that the action correctly lifts containment from an endpoint."""
        crowd_strike_falcon.add_device(MOCK_DATA["get_devices"]["resources"][2])

        LiftContainedEndpoint.main(True)

        assert len(script_session.request_history) == 6
        assert action_output.results.output_message == SUCCESS_OUTPUT_MESSAGE
        assert action_output.results.result_value is True
        assert action_output.results.execution_state == ExecutionState.COMPLETED

    @set_metadata(
        parameters=PARAMS,
        entities=[WRONG_ENTITY],
        integration_config_file_path=CONFIG_PATH,
        input_context=copy.deepcopy(TIMEOUT_CONTEXT),
    )
    def test_list_contain_endpoint_wrong_entity_case(
        self,
        script_session: CrowdStrikeFalconSession,
        action_output: MockActionOutput,
    ) -> None:
        """Verifies the action fails gracefully with an unsupported entity type."""
        LiftContainedEndpoint.main(True)

        assert len(script_session.request_history) == 2
        assert action_output.results.output_message == FAILURE_OUTPUT_MESSAGE
        assert action_output.results.result_value is False
        assert action_output.results.execution_state == ExecutionState.COMPLETED


@pytest.mark.usefixtures("script_session", "setup_device_data")
class TestMemberCID:
    """Tests for multi-tenancy customer ID (CID) handling."""

    @set_metadata(
        parameters=copy.deepcopy(PARENT_TENANT_PARAMS),
        entities=[HOSTNAME_ENTITY],
        integration_config_file_path=CONFIG_PATH,
        input_context=copy.deepcopy(TIMEOUT_CONTEXT),
    )
    def test_parent_tenant_auth_when_no_cid_is_provided(
        self,
        script_session: CrowdStrikeFalconSession,
        action_output: MockActionOutput,
    ) -> None:
        """Verifies authentication targets the parent tenant if no CID is given."""
        LiftContainedEndpoint.main(True)
        history_record: Any = script_session.request_history[0]
        token_payload: dict[str, Any] = history_record.request.kwargs.get("data", {})

        assert "member_cid" not in token_payload
        assert action_output.results.execution_state == ExecutionState.COMPLETED

    @set_metadata(
        parameters=copy.deepcopy(CHILD_TENANT_PARAMS),
        entities=[HOSTNAME_ENTITY],
        integration_config_file_path=CONFIG_PATH,
        input_context=copy.deepcopy(TIMEOUT_CONTEXT),
    )
    def test_child_tenant_auth_when_action_cid_is_provided(
        self,
        script_session: CrowdStrikeFalconSession,
        action_output: MockActionOutput,
    ) -> None:
        """Verifies auth uses the action's CID when provided."""
        LiftContainedEndpoint.main(True)
        history_record: Any = script_session.request_history[0]
        token_payload: dict[str, Any] = history_record.request.kwargs.get(
            "data", {},
        )

        assert token_payload.get("member_cid") == ACTION_CUSTOMER_ID
        assert action_output.results.execution_state == ExecutionState.COMPLETED

    @set_metadata(
        parameters=copy.deepcopy(PARENT_TENANT_PARAMS),
        entities=[HOSTNAME_ENTITY],
        integration_config=INTEGRATION_CONFIG_WITH_CID,
        input_context=copy.deepcopy(TIMEOUT_CONTEXT),
    )
    def test_child_tenant_auth_falls_back_to_integration_cid(
        self,
        script_session: CrowdStrikeFalconSession,
        action_output: MockActionOutput,
    ) -> None:
        """Verifies auth uses the integration's CID if the action's is empty."""
        LiftContainedEndpoint.main(True)
        history_record: Any = script_session.request_history[0]
        token_payload: dict[str, Any] = history_record.request.kwargs.get(
            "data", {},
        )

        assert token_payload.get("member_cid") == INTEGRATION_CUSTOMER_ID
        assert action_output.results.execution_state == ExecutionState.COMPLETED

    @set_metadata(
        parameters=copy.deepcopy(CHILD_TENANT_PARAMS),
        entities=[HOSTNAME_ENTITY],
        integration_config=INTEGRATION_CONFIG_WITH_CID,
        input_context=copy.deepcopy(TIMEOUT_CONTEXT),
    )
    def test_action_cid_overrides_integration_cid(
        self,
        script_session: CrowdStrikeFalconSession,
        action_output: MockActionOutput,
    ) -> None:
        """Verifies that the action's CID takes precedence over the integration's."""
        LiftContainedEndpoint.main(True)

        auth_request: Any = script_session.request_history[0]
        token_payload: dict[str, Any] = auth_request.request.kwargs.get(
            "data", {},
        )
        assert token_payload.get("member_cid") == ACTION_CUSTOMER_ID
        assert action_output.results.execution_state == ExecutionState.COMPLETED

        device_searches = [
            r
            for r in script_session.request_history
            if r.request.url.path == "/devices/queries/devices/v1"
        ]
        assert len(device_searches) >= 2, "Expected at least two device searches"

        device_search_request = device_searches[1]
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


@pytest.mark.usefixtures("script_session")
class TestQueryState:
    """Tests for the action's asynchronous polling loop (QueryState)."""

    @set_metadata(
        parameters={
            **BASE_PARAMS,
            "additional_data": json.dumps({
                "pending": [["HOSTNAME", HOSTNAME_ENTITY_ID]],
                "failed": [],
                "ready": [],
                "skipped": [],
                "containment_pending_endpoints": [HOSTNAME_ENTITY_ID],
            }),
        },
        entities=[HOSTNAME_ENTITY],
        integration_config_file_path=CONFIG_PATH,
        input_context=copy.deepcopy(TIMEOUT_CONTEXT),
    )
    def test_lift_contain_endpoint_query_state_normal_success(
        self,
        crowd_strike_falcon: CrowdStrikeFalcon,
        action_output: MockActionOutput,
    ) -> None:
        """Verifies that when an endpoint transitions to 'normal' during polling,
        lifting containment completes successfully.
        """
        crowd_strike_falcon.add_device({
            "device_id": "device_id_1",
            "hostname": HOSTNAME_ENTITY_ID,
            "status": "normal",
        })

        LiftContainedEndpoint.main(False)

        assert (
            action_output.results.output_message
            == f"Successfully lifted containment on the following endpoints in Crowdstrike Falcon: {HOSTNAME_ENTITY_ID}\n"
        )
        assert action_output.results.result_value is True
        assert action_output.results.execution_state == ExecutionState.COMPLETED

    @set_metadata(
        parameters={
            **BASE_PARAMS,
            "additional_data": json.dumps({
                "pending": [["HOSTNAME", HOSTNAME_ENTITY_ID]],
                "failed": [],
                "ready": [],
                "skipped": [],
                "containment_pending_endpoints": [HOSTNAME_ENTITY_ID],
            }),
        },
        entities=[HOSTNAME_ENTITY],
        integration_config_file_path=CONFIG_PATH,
        input_context=copy.deepcopy(TIMEOUT_CONTEXT),
    )
    def test_lift_contain_endpoint_query_state_still_in_progress(
        self,
        crowd_strike_falcon: CrowdStrikeFalcon,
        action_output: MockActionOutput,
    ) -> None:
        """Verifies that while an endpoint is still 'lift_containment_pending',
        polling continues in progress.
        """
        crowd_strike_falcon.add_device({
            "device_id": "device_id_1",
            "hostname": HOSTNAME_ENTITY_ID,
            "status": "lift_containment_pending",
        })

        LiftContainedEndpoint.main(False)

        assert action_output.results.execution_state == ExecutionState.IN_PROGRESS
        assert (
            action_output.results.output_message
            == f"Waiting for containment lift to finish for the following endpoints: {HOSTNAME_ENTITY_ID}"
        )

    @set_metadata(
        parameters={
            **BASE_PARAMS,
            "additional_data": json.dumps({
                "pending": [["HOSTNAME", HOSTNAME_ENTITY_ID]],
                "failed": [],
                "ready": [],
                "skipped": [],
                "containment_pending_endpoints": [HOSTNAME_ENTITY_ID],
            }),
        },
        entities=[HOSTNAME_ENTITY],
        integration_config_file_path=CONFIG_PATH,
        input_context=copy.deepcopy(TIMEOUT_CONTEXT),
    )
    def test_lift_contain_endpoint_query_state_aborted_on_containment_pending(
        self,
        crowd_strike_falcon: CrowdStrikeFalcon,
        script_session: CrowdStrikeFalconSession,
        action_output: MockActionOutput,
    ) -> None:
        """Verifies that when 'Contain Endpoint' is triggered externally
        (host status becomes 'containment_pending'), the active 'Lift Contained Endpoint'
        polling task gracefully aborts instead of re-lifting or flapping.
        """
        crowd_strike_falcon.add_device({
            "device_id": "device_id_1",
            "hostname": HOSTNAME_ENTITY_ID,
            "status": "containment_pending",
        })

        LiftContainedEndpoint.main(False)

        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert action_output.results.result_value is False
        assert (
            action_output.results.output_message
            == f"Lifting containment was aborted for the following endpoints due to external state change in Crowdstrike Falcon: {HOSTNAME_ENTITY_ID}\n"
        )
        action_requests = [
            r for r in script_session.request_history
            if "devices-actions" in r.request.url.path
        ]
        assert len(action_requests) == 0

    @set_metadata(
        parameters={
            **BASE_PARAMS,
            "additional_data": json.dumps({
                "pending": [["HOSTNAME", HOSTNAME_ENTITY_ID]],
                "failed": [],
                "ready": [],
                "skipped": [],
                "containment_pending_endpoints": [HOSTNAME_ENTITY_ID],
            }),
        },
        entities=[HOSTNAME_ENTITY],
        integration_config_file_path=CONFIG_PATH,
        input_context=copy.deepcopy(TIMEOUT_CONTEXT),
    )
    def test_lift_contain_endpoint_query_state_aborted_on_contained(
        self,
        crowd_strike_falcon: CrowdStrikeFalcon,
        script_session: CrowdStrikeFalconSession,
        action_output: MockActionOutput,
    ) -> None:
        """Verifies that when host state changes externally to 'contained', the active
        lift containment task gracefully aborts instead of re-lifting.
        """
        crowd_strike_falcon.add_device({
            "device_id": "device_id_1",
            "hostname": HOSTNAME_ENTITY_ID,
            "status": "contained",
        })

        LiftContainedEndpoint.main(False)

        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert action_output.results.result_value is False
        assert (
            action_output.results.output_message
            == f"Lifting containment was aborted for the following endpoints due to external state change in Crowdstrike Falcon: {HOSTNAME_ENTITY_ID}\n"
        )
        action_requests = [
            r for r in script_session.request_history
            if "devices-actions" in r.request.url.path
        ]
        assert len(action_requests) == 0
