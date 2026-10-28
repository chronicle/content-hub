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
from crowd_strike_falcon.actions import UpdateAlert
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

ALERT_ID: str = "ind:2a1c5ef609ac479ba77f8ca5879c82fc:412662126878012-10307-9053712"
WRONG_ALERT_ID: str = "no_ids"
STATUS_VALUE: str = "New"
VERDICT_VALUE: str = "True Positive"
SUCCESS_PARAMS: SingleJson = {
    "Alert ID": ALERT_ID,
    "Status": STATUS_VALUE,
    "Verdict": VERDICT_VALUE,
    "Assign To": "",
}
FAIL_PARAMS: SingleJson = {
    "Alert ID": WRONG_ALERT_ID,
    "Status": STATUS_VALUE,
    "Verdict": VERDICT_VALUE,
    "Assign To": "",
}
SUCCESS_OUTPUT_MESSAGE: str = (
    f"Successfully updated alert with ID {ALERT_ID} in Crowdstrike."
)
FAILURE_OUTPUT_MESSAGE: str = (
    'Error executing action "CrowdStrikeFalcon - Update Alert".\nReason: '
    f"alert with ID {WRONG_ALERT_ID} wasn’t found in Crowdstrike. "
    "Please check the spelling."
)

RAW_ALERT_DATA: SingleJson = {
    "id": ALERT_ID,
    "created_timestamp": DEFAULT_TIME_STR,
    "updated_timestamp": DEFAULT_TIME_STR,
}

INTEGRATION_CUSTOMER_ID: str = "integration_cid_for_update_alert"
INTEGRATION_CONFIG_WITH_CID: SingleJson = CONFIG.copy()
INTEGRATION_CONFIG_WITH_CID["Customer ID"] = INTEGRATION_CUSTOMER_ID


@pytest.mark.usefixtures("script_session")
class TestHappyPath:

    @set_metadata(
        parameters=SUCCESS_PARAMS,
        integration_config_file_path=CONFIG_PATH,
    )
    def test_update_alert_success(
        self,
        crowd_strike_falcon: CrowdStrikeFalcon,
        script_session: CrowdStrikeFalconSession,
        action_output: MockActionOutput,
    ) -> None:
        crowd_strike_falcon.add_alert(RAW_ALERT_DATA)
        crowd_strike_falcon.update_alert(ALERT_ID, STATUS_VALUE)

        UpdateAlert.main()

        assert len(script_session.request_history) == 4
        assert action_output.results.output_message == SUCCESS_OUTPUT_MESSAGE
        assert action_output.results.result_value == 1
        assert action_output.results.execution_state == ExecutionState.COMPLETED

    @set_metadata(
        parameters=FAIL_PARAMS,
        integration_config_file_path=CONFIG_PATH,
    )
    def test_update_alert_wrong_id(
        self,
        script_session: CrowdStrikeFalconSession,
        action_output: MockActionOutput,
    ) -> None:
        UpdateAlert.main()

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
        UpdateAlert.main()

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
        UpdateAlert.main()

        history_record: Any = script_session.request_history[0]
        token_request_payload: dict[str, Any] = history_record.request.kwargs.get(
            "data", {},
        )
        assert token_request_payload.get("member_cid") == INTEGRATION_CUSTOMER_ID
