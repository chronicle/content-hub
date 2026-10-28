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
from crowd_strike_falcon.actions import GetEventOffset
from TIPCommon.base.action import ExecutionState
from TIPCommon.types import SingleJson

from crowd_strike_falcon.tests.common import CONFIG_PATH, MOCK_DATA
from crowd_strike_falcon.tests.core.crowd_strike_falcon import (
    CrowdStrikeFalcon,
)
from crowd_strike_falcon.tests.core.session import CrowdStrikeFalconSession
from crowd_strike_falcon.tests.test_constants import DEFAULT_TIME_STR
from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata

MAX_EVENT_LIMIT: int = 1
INTEGRATION_CUSTOMER_ID: str = "integration_cid_404"

DETECTION_ID: str = "2a1c5ef609ac479ba77f8ca5879c82fc"
MOCK_DATA["get_discover_streams_v1"]["first_behavior"] = DEFAULT_TIME_STR
MOCK_DATA["get_discover_streams_v1"]["last_behavior"] = DEFAULT_TIME_STR

SUCCESS_PARAMS: SingleJson = {"Max Events To Process": MAX_EVENT_LIMIT}

INTEGRATION_CONFIG_WITH_CID: SingleJson = {
    "API Root": "https://api.crowdstrike.com",
    "Client API ID": "dummy",
    "Client API Secret": "dummy",
    "Verify SSL": "False",
    "Customer ID": INTEGRATION_CUSTOMER_ID,
}

SUCCESS_OUTPUT_MESSAGE: str = (
    "Successfully retrieved event offset in Crowdstrike Falcon."
)


@pytest.mark.usefixtures("script_session")
class TestHappyPath:

    @set_metadata(
        parameters={"Max Events To Process": MAX_EVENT_LIMIT},
        integration_config_file_path=CONFIG_PATH,
    )
    def test_get_event_offset_success(
        self,
        script_session: CrowdStrikeFalconSession,
        crowd_strike_falcon: CrowdStrikeFalcon,
        action_output: MockActionOutput,
    ) -> None:
        crowd_strike_falcon.add_stream_detection(
            MOCK_DATA["get_discover_streams_v1"],
        )

        GetEventOffset.main()

        assert len(script_session.request_history) == 3
        assert action_output.results.output_message == SUCCESS_OUTPUT_MESSAGE
        assert action_output.results.result_value is True
        assert action_output.results.execution_state == ExecutionState.COMPLETED


    @set_metadata(
        parameters=SUCCESS_PARAMS,
        integration_config_file_path=CONFIG_PATH,
    )
    def test_parent_tenant_auth_does_not_send_member_cid(
        self,
        script_session: CrowdStrikeFalconSession,
        crowd_strike_falcon: CrowdStrikeFalcon,
    ) -> None:
        """Verifies authentication request does not contain member_cid
        when no CID is provided.
        """
        crowd_strike_falcon.add_stream_detection(
            MOCK_DATA["get_discover_streams_v1"],
        )
        GetEventOffset.main()

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
        script_session: CrowdStrikeFalconSession,
        crowd_strike_falcon: CrowdStrikeFalcon,
    ) -> None:
        """Verifies auth request uses the integration's CID when provided."""
        crowd_strike_falcon.add_stream_detection(
            MOCK_DATA["get_discover_streams_v1"],
        )
        GetEventOffset.main()

        history_record: Any = script_session.request_history[0]
        token_request_payload: dict[str, Any] = history_record.request.kwargs.get(
            "data", {},
        )
        assert token_request_payload.get("member_cid") == INTEGRATION_CUSTOMER_ID
