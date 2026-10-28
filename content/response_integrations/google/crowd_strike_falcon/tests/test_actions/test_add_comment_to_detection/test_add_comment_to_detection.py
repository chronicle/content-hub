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

import uuid
from typing import Any

import pytest
from crowd_strike_falcon.actions import AddCommentToDetection
from TIPCommon.base.action import ExecutionState
from TIPCommon.types import SingleJson

from crowd_strike_falcon.tests.common import CONFIG_PATH
from crowd_strike_falcon.tests.core.crowd_strike_falcon import CrowdStrikeFalcon
from crowd_strike_falcon.tests.core.session import CrowdStrikeFalconSession
from crowd_strike_falcon.tests.test_constants import (
    COMMENT,
    DEFAULT_TIME_STR,
    NO_IDS,
)
from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata

DETECTION_ID: str = str(uuid.uuid4())
INTEGRATION_CUSTOMER_ID: str = "integration_cid_456"

DETECTION_DATA: SingleJson = {
    "detection_id": DETECTION_ID,
    "first_behavior": DEFAULT_TIME_STR,
    "last_behavior": DEFAULT_TIME_STR,
}

SUCCESS_PARAMS: SingleJson = {"Detection ID": DETECTION_ID, "Comment": COMMENT}
NO_DETECT_ID_PARAMS: SingleJson = {"Detection ID": NO_IDS, "Comment": COMMENT}

INTEGRATION_CONFIG_WITH_CID: SingleJson = {
    "API Root": "https://api.crowdstrike.com",
    "Client API ID": "dummy",
    "Client API Secret": "dummy",
    "Verify SSL": "False",
    "Customer ID": INTEGRATION_CUSTOMER_ID,
}

SUCCESS_OUTPUT_MESSAGE: str = (
    f"Successfully added comment to detection with identifier: {DETECTION_ID}."
)
FAILURE_OUTPUT_MESSAGE: str = (
    "Error executing action 'CrowdStrikeFalcon - Add Comment to Detection'. Reason: "
    f"Unable to get status of the detection with identifier {NO_IDS}: invalid "
    "element in the request"
)


@pytest.mark.usefixtures("script_session")
class TestHappyPath:

    @set_metadata(
        parameters=SUCCESS_PARAMS,
        integration_config_file_path=CONFIG_PATH,
    )
    def test_add_comment_to_detection_success(
        self,
        crowd_strike_falcon: CrowdStrikeFalcon,
        script_session: CrowdStrikeFalconSession,
        action_output: MockActionOutput,
    ) -> None:
        crowd_strike_falcon.add_detection(DETECTION_DATA)

        AddCommentToDetection.main()

        assert len(script_session.request_history) == 3
        assert action_output.results.output_message == SUCCESS_OUTPUT_MESSAGE
        assert action_output.results.result_value is True
        assert action_output.results.execution_state == ExecutionState.COMPLETED

    @set_metadata(
        parameters=NO_DETECT_ID_PARAMS,
        integration_config_file_path=CONFIG_PATH,
    )
    def test_add_comment_to_detection_no_detection_id(
            self,
            script_session: CrowdStrikeFalconSession,
            action_output: MockActionOutput,
    ) -> None:
        AddCommentToDetection.main()

        assert len(script_session.request_history) == 2
        assert action_output.results.output_message == FAILURE_OUTPUT_MESSAGE
        assert action_output.results.result_value is False
        assert action_output.results.execution_state == ExecutionState.FAILED


    @set_metadata(
        parameters=SUCCESS_PARAMS,
        integration_config_file_path=CONFIG_PATH,
    )
    def test_parent_tenant_auth_does_not_send_member_cid(
        self,
        crowd_strike_falcon: CrowdStrikeFalcon,
        script_session: CrowdStrikeFalconSession,
    ) -> None:
        """Verifies authentication request does not contain member_cid
        when no CID is provided.
        """
        crowd_strike_falcon.add_detection(DETECTION_DATA)
        AddCommentToDetection.main()

        history_record: Any = script_session.request_history[0]
        token_request_payload: dict[str, Any] = history_record.request.kwargs.get(
            "data", {},
        )
        assert "member_cid" not in token_request_payload

    @set_metadata(
        parameters=SUCCESS_PARAMS,
        integration_config=INTEGRATION_CONFIG_WITH_CID,
    )
    def test_child_tenant_auth_sends_integration_member_cid(
        self,
        crowd_strike_falcon: CrowdStrikeFalcon,
        script_session: CrowdStrikeFalconSession,
    ) -> None:
        """Verifies auth request uses the integration's CID when provided."""
        crowd_strike_falcon.add_detection(DETECTION_DATA)
        AddCommentToDetection.main()

        history_record: Any = script_session.request_history[0]
        token_request_payload: dict[str, Any] = history_record.request.kwargs.get(
            "data", {},
        )
        assert token_request_payload.get("member_cid") == INTEGRATION_CUSTOMER_ID
