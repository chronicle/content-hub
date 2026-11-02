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

from crowd_strike_falcon.actions import GetAlertDetails
from TIPCommon.base.action import ExecutionState
from TIPCommon.types import SingleJson

from crowd_strike_falcon.tests.common import CONFIG_PATH
from crowd_strike_falcon.tests.core.crowd_strike_falcon import (
    CrowdStrikeFalcon,
)
from crowd_strike_falcon.tests.core.session import CrowdStrikeFalconSession
from crowd_strike_falcon.tests.test_constants import DEFAULT_TIME_STR
from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata

ALERT_ID: str = "ind:2a1c5ef609ac479ba77f8ca5879c82fc:412662126878012-10307-9053712"
WRONG_ALERT_ID: str = "no_ids"
SUCCESS_PARAMS: SingleJson = {
    "Alert ID": ALERT_ID,
}
FAIL_PARAMS: SingleJson = {
    "Alert ID": WRONG_ALERT_ID,
}
SUCCESS_OUTPUT_MESSAGE: str = (
    f"Successfully returned information about the alert with ID {ALERT_ID} in "
    "Crowdstrike."
)
FAILURE_OUTPUT_MESSAGE: str = (
    'Error executing action "CrowdStrikeFalcon - Get Alert Details"\nReason: '
    f"alert with ID {WRONG_ALERT_ID} wasn’t found in Crowdstrike. "
    "Please check the spelling."
)


class TestGetAlertDetails:

    @set_metadata(
        parameters=SUCCESS_PARAMS,
        integration_config_file_path=CONFIG_PATH,
    )
    def test_get_alert_details_success(
        self,
        crowd_strike_falcon: CrowdStrikeFalcon,
        script_session: CrowdStrikeFalconSession,
        action_output: MockActionOutput,
    ) -> None:
        raw_alert_data: SingleJson = {
            "id": ALERT_ID,
            "created_timestamp": DEFAULT_TIME_STR,
            "updated_timestamp": DEFAULT_TIME_STR,
        }
        crowd_strike_falcon.add_alert(raw_alert_data)

        GetAlertDetails.main()

        assert len(script_session.request_history) == 2
        assert action_output.results.output_message == SUCCESS_OUTPUT_MESSAGE
        assert action_output.results.result_value == 1
        assert action_output.results.execution_state == ExecutionState.COMPLETED

    @set_metadata(
        parameters=FAIL_PARAMS,
        integration_config_file_path=CONFIG_PATH,
    )
    def test_get_alert_details_wrong_id(
        self,
        script_session: CrowdStrikeFalconSession,
        action_output: MockActionOutput,
    ) -> None:
        GetAlertDetails.main()

        assert len(script_session.request_history) == 2
        assert action_output.results.output_message == FAILURE_OUTPUT_MESSAGE
        assert action_output.results.execution_state == ExecutionState.FAILED
