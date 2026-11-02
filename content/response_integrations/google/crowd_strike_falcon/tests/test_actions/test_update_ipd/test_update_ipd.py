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

from typing import Any

import pytest
from crowd_strike_falcon.actions import UpdateIdentityProtectionDetection
from crowd_strike_falcon.core.datamodels import AlertDetails
from TIPCommon.base.action import ExecutionState
from TIPCommon.types import SingleJson

from crowd_strike_falcon.tests.common import CONFIG, CONFIG_PATH
from crowd_strike_falcon.tests.core.crowd_strike_falcon import (
    CrowdStrikeFalcon,
)
from crowd_strike_falcon.tests.core.session import CrowdStrikeFalconSession
from crowd_strike_falcon.tests.test_constants import DEFAULT_TIME_STR
from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata

DETECTION_ID: str = "ldt:2a1c5ef609ac479ba77f8ca5879c82fc:3617341609124"
WRONG_DETECTION_ID: str = "no_ids"
STATUS_VALUE: str = "New"
UPDATE_STATUS_VALUE: str = "new"
VERDICT_VALUE: str = "True Positive"
SUCCESS_PARAMS: SingleJson = {
    "Detection ID": DETECTION_ID,
    "Status": STATUS_VALUE,
    "Assign Detection to": "",
}
FAILED_PARAMS: SingleJson = {
    "Detection ID": WRONG_DETECTION_ID,
    "Status": STATUS_VALUE,
    "Assign Detection to": "",
}
SUCCESS_OUTPUT_MESSAGE: str = (
    f"Successfully updated identity protection detection with ID {DETECTION_ID} "
    "in CrowdStrikeFalcon."
)
FAILURE_OUTPUT_MESSAGE: str = (
    'Error executing action "CrowdStrikeFalcon - Update Identity Protection Detection'
    '". Reason: An error occurred: invalid element in the request'
)

RAW_ALERT_DATA: SingleJson = {
    "id": DETECTION_ID,
    "created_timestamp": DEFAULT_TIME_STR,
    "updated_timestamp": DEFAULT_TIME_STR,
}

INTEGRATION_CUSTOMER_ID: str = "integration_cid_for_update_ipd"
INTEGRATION_CONFIG_WITH_CID: SingleJson = CONFIG.copy()
INTEGRATION_CONFIG_WITH_CID["Customer ID"] = INTEGRATION_CUSTOMER_ID


@pytest.mark.usefixtures("script_session")
class TestHappyPath:

    @set_metadata(
        parameters=SUCCESS_PARAMS,
        integration_config_file_path=CONFIG_PATH,
    )
    def test_update_ipd_success(
        self,
        crowd_strike_falcon: CrowdStrikeFalcon,
        script_session: CrowdStrikeFalconSession,
        action_output: MockActionOutput,
    ) -> None:
        crowd_strike_falcon.add_alert(RAW_ALERT_DATA)
        crowd_strike_falcon.update_alert(DETECTION_ID, UPDATE_STATUS_VALUE)
        alert: AlertDetails = crowd_strike_falcon.get_alert(DETECTION_ID)

        UpdateIdentityProtectionDetection.main()

        assert (
            action_output.results.json_output.json_result["status"]
            ==
            alert.raw_data["status"]
        )
        assert len(script_session.request_history) == 4
        assert action_output.results.output_message == SUCCESS_OUTPUT_MESSAGE
        assert action_output.results.result_value == 1
        assert action_output.results.execution_state == ExecutionState.COMPLETED

    @set_metadata(
        parameters=FAILED_PARAMS,
        integration_config_file_path=CONFIG_PATH,
    )
    def test_update_ipd_with_wrong_id(
        self,
        script_session: CrowdStrikeFalconSession,
        action_output: MockActionOutput,
    ) -> None:
        UpdateIdentityProtectionDetection.main()

        assert len(script_session.request_history) == 2
        assert action_output.results.output_message == FAILURE_OUTPUT_MESSAGE
        assert action_output.results.execution_state == ExecutionState.FAILED


@pytest.mark.usefixtures("script_session")
class TestTenantAuthentication:
    """Tests the tenant authentication logic based on integration configuration."""

    @set_metadata(
        parameters=SUCCESS_PARAMS,
        integration_config_file_path=CONFIG_PATH,
    )
    def test_parent_tenant_auth_when_no_cid_in_config(
        self,
        crowd_strike_falcon: CrowdStrikeFalcon,
        script_session: CrowdStrikeFalconSession,
    ) -> None:
        """Verifies that 'member_cid' is not sent when the integration config
        does not contain a Customer ID.
        """
        crowd_strike_falcon.add_alert(RAW_ALERT_DATA)
        UpdateIdentityProtectionDetection.main()

        history_record: Any = script_session.request_history[0]
        token_request_payload: dict[str, Any] = history_record.request.kwargs.get(
            "data", {},
        )
        assert "member_cid" not in token_request_payload

    @set_metadata(
        parameters=SUCCESS_PARAMS,
        integration_config=INTEGRATION_CONFIG_WITH_CID,
    )
    def test_child_tenant_auth_when_cid_is_in_config(
        self,
        crowd_strike_falcon: CrowdStrikeFalcon,
        script_session: CrowdStrikeFalconSession,
    ) -> None:
        """Verifies that 'member_cid' is sent when the integration config
        contains a Customer ID.
        """
        crowd_strike_falcon.add_alert(RAW_ALERT_DATA)
        UpdateIdentityProtectionDetection.main()

        history_record: Any = script_session.request_history[0]
        token_request_payload: dict[str, Any] = history_record.request.kwargs.get(
            "data", {},
        )
        assert token_request_payload.get("member_cid") == INTEGRATION_CUSTOMER_ID
