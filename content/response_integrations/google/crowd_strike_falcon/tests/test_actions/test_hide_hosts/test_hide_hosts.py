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

import pytest
from crowd_strike_falcon.actions import HideHosts
from crowd_strike_falcon.tests.common import (
    CONFIG_PATH,
    HOSTNAME_ENTITY,
    HOSTNAME_ENTITY_ID,
)
from crowd_strike_falcon.tests.core.crowd_strike_falcon import (
    CrowdStrikeFalcon,
)
from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata
from TIPCommon.base.action import ExecutionState
from TIPCommon.types import SingleJson

DEVICE_ID: str = "device_1"
DEVICE_DATA: SingleJson = {
    "device_id": DEVICE_ID,
    "hostname": HOSTNAME_ENTITY_ID,
}

SUCCESS_PARAMS_WITH_ENTITY: SingleJson = {"Hostname": ""}
SUCCESS_PARAMS_WITH_HOSTNAME: SingleJson = {"Hostname": HOSTNAME_ENTITY_ID}
SUCCESS_PARAMS_WITH_DEVICE_ID: SingleJson = {"Device ID": DEVICE_ID}

SUCCESS_OUTPUT_MESSAGE: str = (
    "Successfully hid the following hosts in Crowdstrike: " f"{HOSTNAME_ENTITY_ID}."
)
SUCCESS_DEVICE_ID_OUTPUT_MESSAGE: str = (
    "Successfully hid the following hosts in Crowdstrike: " f"{DEVICE_ID}."
)
FAILURE_OUTPUT_MESSAGE: str = "None of the provided hosts were hidden."


@pytest.mark.usefixtures("script_session")
class TestHappyPath:

    @set_metadata(
        parameters=SUCCESS_PARAMS_WITH_ENTITY,
        integration_config_file_path=CONFIG_PATH,
        entities=[HOSTNAME_ENTITY],
    )
    def test_hide_host_with_entity_success(
        self,
        crowd_strike_falcon: CrowdStrikeFalcon,
        action_output: MockActionOutput,
    ) -> None:
        crowd_strike_falcon.add_device(DEVICE_DATA)

        HideHosts.main()

        assert action_output.results.result_value is True
        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert action_output.results.output_message == SUCCESS_OUTPUT_MESSAGE

    @set_metadata(
        parameters=SUCCESS_PARAMS_WITH_DEVICE_ID,
        integration_config_file_path=CONFIG_PATH,
        entities=[],
    )
    def test_hide_host_with_device_id_success(
        self,
        crowd_strike_falcon: CrowdStrikeFalcon,
        action_output: MockActionOutput,
    ) -> None:
        crowd_strike_falcon.add_device(DEVICE_DATA)

        HideHosts.main()

        assert action_output.results.result_value is True
        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert action_output.results.output_message == SUCCESS_DEVICE_ID_OUTPUT_MESSAGE

    @set_metadata(
        parameters={"Device ID": DEVICE_ID},
        integration_config_file_path=CONFIG_PATH,
        entities=[HOSTNAME_ENTITY],
    )
    def test_hide_host_with_entity_and_device_id_deduplication(
        self,
        crowd_strike_falcon: CrowdStrikeFalcon,
        action_output: MockActionOutput,
    ) -> None:
        crowd_strike_falcon.add_device(DEVICE_DATA)

        HideHosts.main()

        assert action_output.results.result_value is True
        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert action_output.results.output_message == SUCCESS_OUTPUT_MESSAGE
        assert len(action_output.results.json_output.json_result) == 1
        assert action_output.results.json_output.json_result[0]["Entity"] == HOSTNAME_ENTITY_ID


@pytest.mark.usefixtures("script_session")
class TestFailurePath:

    @set_metadata(
        parameters=SUCCESS_PARAMS_WITH_ENTITY,
        integration_config_file_path=CONFIG_PATH,
        entities=[HOSTNAME_ENTITY],
    )
    def test_hide_host_device_not_found(
        self,
        action_output: MockActionOutput,
    ) -> None:
        HideHosts.main()

        assert action_output.results.result_value is False
        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert FAILURE_OUTPUT_MESSAGE in action_output.results.output_message

    @set_metadata(
        parameters=SUCCESS_PARAMS_WITH_DEVICE_ID,
        integration_config_file_path=CONFIG_PATH,
        entities=[],
    )
    def test_hide_host_device_id_not_found(
        self,
        action_output: MockActionOutput,
    ) -> None:
        HideHosts.main()

        assert action_output.results.result_value is False
        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert FAILURE_OUTPUT_MESSAGE in action_output.results.output_message

    @set_metadata(
        parameters={"Device ID": "device_unicode_åäö"},
        integration_config_file_path=CONFIG_PATH,
        entities=[],
    )
    def test_hide_host_unicode_device_id_failure(
        self,
        action_output: MockActionOutput,
    ) -> None:
        HideHosts.main()

        assert action_output.results.result_value is False
        assert action_output.results.execution_state == ExecutionState.FAILED
        assert "Device ID cannot contain unicode characters." in action_output.results.output_message
