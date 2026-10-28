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

import copy
import datetime
import json
from typing import Any

import pytest
from crowd_strike_falcon.actions import ContainEndpoint
from TIPCommon.base.action import EntityTypesEnum, ExecutionState
from TIPCommon.types import Entity, SingleJson

from crowd_strike_falcon.tests.common import (
    CONFIG_PATH,
    HOSTNAME_ENTITY,
    HOSTNAME_ENTITY_ID,
    MOCK_DATA,
)
from crowd_strike_falcon.tests.core.crowd_strike_falcon import (
    CrowdStrikeFalcon,
)
from crowd_strike_falcon.tests.core.session import CrowdStrikeFalconSession
from integration_testing.common import create_entity
from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata

HOSTNAME2_ENTITY_ID: str = "npatni-sysopss"
HOSTNAME2_ENTITY: Entity = create_entity(HOSTNAME2_ENTITY_ID, EntityTypesEnum.HOST_NAME)

BASE_PARAMS: SingleJson = {"Fail If Timeout": False}
SUCCESS_OUTPUT_MESSAGE: str = (
    f"The following endpoints were already contained Crowdstrike Falcon: "
    f"{HOSTNAME_ENTITY_ID}\n"
)
IN_PROGRESS_OUTPUT_MESSAGE: str = (
    "Waiting for containment to finish for the following endpoints: "
    f"{HOSTNAME2_ENTITY_ID}"
)
IN_PROGRESS_RESULT_VALUE: str = (
    '{"pending": [["HOSTNAME", "npatni-sysopss"]], "failed": [], "ready": [], '
    '"skipped": [], "containment_pending_endpoints": ["npatni-sysopss"]}'
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

PARENT_TENANT_PARAMS: SingleJson = {**BASE_PARAMS, "Customer ID": ""}
CHILD_TENANT_PARAMS: SingleJson = {**BASE_PARAMS, "Customer ID": ACTION_CUSTOMER_ID}
DEVICE_ID_PARAMS: SingleJson = {**BASE_PARAMS, "Device ID": "device_id_1"}

INTEGRATION_CONFIG_WITH_CID: SingleJson = {
    "API Root": "https://api.crowdstrike.com",
    "Client API ID": "dummy",
    "Client API Secret": "dummy",
    "Verify SSL": "False",
    "Customer ID": INTEGRATION_CUSTOMER_ID,
}


@pytest.mark.usefixtures("script_session")
class TestHappyPath:

    @set_metadata(
        parameters=DEVICE_ID_PARAMS,
        entities=[],
        integration_config_file_path=CONFIG_PATH,
        input_context=copy.deepcopy(TIMEOUT),
    )
    def test_contain_endpoint_with_device_id_success(
        self,
        crowd_strike_falcon: CrowdStrikeFalcon,
        action_output: MockActionOutput,
    ) -> None:
        crowd_strike_falcon.add_device({
            "device_id": "device_id_1",
            "hostname": "device_id_1",
            "status": "contained",
        })

        ContainEndpoint.main(True)

        assert action_output.results.output_message == "The following endpoints were already contained Crowdstrike Falcon: device_id_1\n"
        assert action_output.results.result_value is True
        assert action_output.results.execution_state == ExecutionState.COMPLETED

    @set_metadata(
        parameters=CHILD_TENANT_PARAMS,
        entities=[HOSTNAME_ENTITY],
        integration_config_file_path=CONFIG_PATH,
        input_context=copy.deepcopy(TIMEOUT),
    )
    def test_contain_endpoint_success(
        self,
        crowd_strike_falcon: CrowdStrikeFalcon,
        action_output: MockActionOutput,
    ) -> None:
        crowd_strike_falcon.add_device(MOCK_DATA["get_devices"]["resources"][0])

        ContainEndpoint.main(True)

        assert action_output.results.output_message == SUCCESS_OUTPUT_MESSAGE
        assert action_output.results.result_value is True
        assert action_output.results.execution_state == ExecutionState.COMPLETED

    @set_metadata(
        parameters=CHILD_TENANT_PARAMS,
        entities=[HOSTNAME2_ENTITY],
        integration_config_file_path=CONFIG_PATH,
        input_context=copy.deepcopy(TIMEOUT),
    )
    def test_contain_endpoint_in_progress(
        self,
        crowd_strike_falcon: CrowdStrikeFalcon,
        action_output: MockActionOutput,
    ) -> None:
        crowd_strike_falcon.add_device(MOCK_DATA["get_devices"]["resources"][2])

        ContainEndpoint.main(True)

        assert action_output.results.output_message == IN_PROGRESS_OUTPUT_MESSAGE
        assert action_output.results.result_value == IN_PROGRESS_RESULT_VALUE
        assert action_output.results.execution_state == ExecutionState.IN_PROGRESS


@pytest.mark.usefixtures("script_session")
class TestMemberCID:

    @set_metadata(
        parameters=PARENT_TENANT_PARAMS,
        entities=[HOSTNAME2_ENTITY],
        integration_config_file_path=CONFIG_PATH,
        input_context=copy.deepcopy(TIMEOUT),
    )
    def test_parent_tenant_auth_when_no_cid_is_provided(
        self,
        crowd_strike_falcon: CrowdStrikeFalcon,
        script_session: CrowdStrikeFalconSession,
        action_output: MockActionOutput,
    ) -> None:
        """Tests the default behavior where no Customer ID is provided. The
        authentication request should target the parent tenant by not including
        the 'member_cid' field.
        """
        crowd_strike_falcon.add_device(MOCK_DATA["get_devices"]["resources"][2])

        ContainEndpoint.main(True)

        history_record: Any = script_session.request_history[0]
        token_request_payload: dict[str, Any] = history_record.request.kwargs.get(
            "data", {},
        )

        assert "member_cid" not in token_request_payload
        assert action_output.results.execution_state == ExecutionState.IN_PROGRESS

    @set_metadata(
        parameters=CHILD_TENANT_PARAMS,
        entities=[HOSTNAME2_ENTITY],
        integration_config_file_path=CONFIG_PATH,
        input_context=copy.deepcopy(TIMEOUT),
    )
    def test_child_tenant_auth_when_action_cid_is_provided(
        self,
        crowd_strike_falcon: CrowdStrikeFalcon,
        script_session: CrowdStrikeFalconSession,
        action_output: MockActionOutput,
    ) -> None:
        """Tests that providing a Customer ID in the action parameters correctly
        targets a child tenant for authentication.
        """
        crowd_strike_falcon.add_device(MOCK_DATA["get_devices"]["resources"][2])

        ContainEndpoint.main(True)

        history_record: Any = script_session.request_history[0]
        token_request_payload: dict[str, Any] = history_record.request.kwargs.get(
            "data", {},
        )

        assert token_request_payload.get("member_cid") == ACTION_CUSTOMER_ID
        assert action_output.results.execution_state == ExecutionState.IN_PROGRESS

    @set_metadata(
        parameters=PARENT_TENANT_PARAMS,
        entities=[HOSTNAME2_ENTITY],
        integration_config=INTEGRATION_CONFIG_WITH_CID,
        input_context=copy.deepcopy(TIMEOUT),
    )
    def test_child_tenant_auth_falls_back_to_integration_cid(
        self,
        crowd_strike_falcon: CrowdStrikeFalcon,
        script_session: CrowdStrikeFalconSession,
        action_output: MockActionOutput,
    ) -> None:
        """Tests the fallback behavior where the action parameters do not contain
        a Customer ID, but one is set in the integration configuration.
        """
        crowd_strike_falcon.add_device(MOCK_DATA["get_devices"]["resources"][2])

        ContainEndpoint.main(True)

        history_record: Any = script_session.request_history[0]
        token_request_payload: dict[str, Any] = history_record.request.kwargs.get(
            "data", {},
        )

        assert token_request_payload.get("member_cid") == INTEGRATION_CUSTOMER_ID
        assert action_output.results.execution_state == ExecutionState.IN_PROGRESS

    @set_metadata(
        parameters=CHILD_TENANT_PARAMS,
        entities=[HOSTNAME2_ENTITY],
        integration_config=INTEGRATION_CONFIG_WITH_CID,
        input_context=copy.deepcopy(TIMEOUT),
    )
    def test_action_cid_overrides_integration_cid(
        self,
        crowd_strike_falcon: CrowdStrikeFalcon,
        script_session: CrowdStrikeFalconSession,
        action_output: MockActionOutput,
    ) -> None:
        """Tests the override behavior where a Customer ID is provided in both the
        action parameters and the integration configuration. The action-level
        CID must take precedence.
        """
        crowd_strike_falcon.add_device(MOCK_DATA["get_devices"]["resources"][2])

        ContainEndpoint.main(True)

        history_record: Any = script_session.request_history[0]
        token_request_payload: dict[str, Any] = history_record.request.kwargs.get(
            "data", {},
        )

        assert token_request_payload.get("member_cid") == ACTION_CUSTOMER_ID
        assert action_output.results.execution_state == ExecutionState.IN_PROGRESS


@pytest.mark.usefixtures("script_session")
class TestQueryState:
    """Tests for the action's asynchronous polling loop (QueryState)."""

    @set_metadata(
        parameters={
            **BASE_PARAMS,
            "additional_data": json.dumps({
                "pending": [["HOSTNAME", HOSTNAME2_ENTITY_ID]],
                "failed": [],
                "ready": [],
                "skipped": [],
                "containment_pending_endpoints": [HOSTNAME2_ENTITY_ID],
            }),
        },
        entities=[HOSTNAME2_ENTITY],
        integration_config_file_path=CONFIG_PATH,
        input_context=copy.deepcopy(TIMEOUT),
    )
    def test_contain_endpoint_query_state_contained_success(
        self,
        crowd_strike_falcon: CrowdStrikeFalcon,
        action_output: MockActionOutput,
    ) -> None:
        """Verifies that when an endpoint transitions to 'contained' during polling,
        it completes successfully.
        """
        device_data = copy.deepcopy(MOCK_DATA["get_devices"]["resources"][2])
        device_data["status"] = "contained"
        crowd_strike_falcon.add_device(device_data)

        ContainEndpoint.main(False)

        assert (
            action_output.results.output_message
            == f"Successfully contained the following endpoints in Crowdstrike Falcon: {HOSTNAME2_ENTITY_ID}\n"
        )
        assert action_output.results.result_value is True
        assert action_output.results.execution_state == ExecutionState.COMPLETED

    @set_metadata(
        parameters={
            **BASE_PARAMS,
            "additional_data": json.dumps({
                "pending": [["HOSTNAME", HOSTNAME2_ENTITY_ID]],
                "failed": [],
                "ready": [],
                "skipped": [],
                "containment_pending_endpoints": [HOSTNAME2_ENTITY_ID],
            }),
        },
        entities=[HOSTNAME2_ENTITY],
        integration_config_file_path=CONFIG_PATH,
        input_context=copy.deepcopy(TIMEOUT),
    )
    def test_contain_endpoint_query_state_still_in_progress(
        self,
        crowd_strike_falcon: CrowdStrikeFalcon,
        action_output: MockActionOutput,
    ) -> None:
        """Verifies that while an endpoint is still 'containment_pending', polling
        continues in progress without re-initiating containment.
        """
        device_data = copy.deepcopy(MOCK_DATA["get_devices"]["resources"][2])
        device_data["status"] = "containment_pending"
        crowd_strike_falcon.add_device(device_data)

        ContainEndpoint.main(False)

        assert action_output.results.execution_state == ExecutionState.IN_PROGRESS
        assert (
            action_output.results.output_message
            == f"Waiting for containment to finish for the following endpoints: {HOSTNAME2_ENTITY_ID}"
        )

    @set_metadata(
        parameters={
            **BASE_PARAMS,
            "additional_data": json.dumps({
                "pending": [["HOSTNAME", HOSTNAME2_ENTITY_ID]],
                "failed": [],
                "ready": [],
                "skipped": [],
                "containment_pending_endpoints": [HOSTNAME2_ENTITY_ID],
            }),
        },
        entities=[HOSTNAME2_ENTITY],
        integration_config_file_path=CONFIG_PATH,
        input_context=copy.deepcopy(TIMEOUT),
    )
    def test_contain_endpoint_query_state_aborted_on_lift_pending(
        self,
        crowd_strike_falcon: CrowdStrikeFalcon,
        script_session: CrowdStrikeFalconSession,
        action_output: MockActionOutput,
    ) -> None:
        """Verifies that when 'Lift Contained Endpoint' is triggered externally
        (host status becomes 'lift_containment_pending'), the active 'Contain Endpoint'
        polling task gracefully aborts instead of re-containing or flapping.
        """
        device_data = copy.deepcopy(MOCK_DATA["get_devices"]["resources"][2])
        device_data["status"] = "lift_containment_pending"
        crowd_strike_falcon.add_device(device_data)

        ContainEndpoint.main(False)

        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert action_output.results.result_value is False
        assert (
            action_output.results.output_message
            == f"Containment was aborted for the following endpoints due to external state change in Crowdstrike Falcon: {HOSTNAME2_ENTITY_ID}\n"
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
                "pending": [["HOSTNAME", HOSTNAME2_ENTITY_ID]],
                "failed": [],
                "ready": [],
                "skipped": [],
                "containment_pending_endpoints": [HOSTNAME2_ENTITY_ID],
            }),
        },
        entities=[HOSTNAME2_ENTITY],
        integration_config_file_path=CONFIG_PATH,
        input_context=copy.deepcopy(TIMEOUT),
    )
    def test_contain_endpoint_query_state_aborted_on_normal(
        self,
        crowd_strike_falcon: CrowdStrikeFalcon,
        script_session: CrowdStrikeFalconSession,
        action_output: MockActionOutput,
    ) -> None:
        """Verifies that when host state changes externally to 'normal', the active
        containment task gracefully aborts instead of re-containing.
        """
        device_data = copy.deepcopy(MOCK_DATA["get_devices"]["resources"][2])
        device_data["status"] = "normal"
        crowd_strike_falcon.add_device(device_data)

        ContainEndpoint.main(False)

        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert action_output.results.result_value is False
        assert (
            action_output.results.output_message
            == f"Containment was aborted for the following endpoints due to external state change in Crowdstrike Falcon: {HOSTNAME2_ENTITY_ID}\n"
        )
        action_requests = [
            r for r in script_session.request_history
            if "devices-actions" in r.request.url.path
        ]
        assert len(action_requests) == 0
