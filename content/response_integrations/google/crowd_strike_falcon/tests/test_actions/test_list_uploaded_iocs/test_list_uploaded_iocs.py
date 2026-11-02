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
from crowd_strike_falcon.actions import ListUploadedIOCs
from TIPCommon.base.action import ExecutionState
from TIPCommon.types import SingleJson

from crowd_strike_falcon.tests.common import CONFIG_PATH, MOCK_DATA
from crowd_strike_falcon.tests.core.crowd_strike_falcon import (
    CrowdStrikeFalcon,
)
from crowd_strike_falcon.tests.core.session import CrowdStrikeFalconSession
from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata

MAX_HOSTS_LIMIT: int = 1
SUCCESS_PARAMS: SingleJson = {
    "Max IOCs To Return": MAX_HOSTS_LIMIT,
    "IOC Type Filter": "",
    "Value Filter Logic": "Equal",
    "Value Filter String": "",
}
FAILED_PARAMS: SingleJson = {
    "Max IOCs To Return": MAX_HOSTS_LIMIT,
    "IOC Type Filter": "any",
    "Value Filter Logic": "Equal",
    "Value Filter String": "",
}
SUCCESS_OUTPUT_MESSAGE: str = (
    "Successfully found custom IOCs for the provided criteria in Crowdstrike Falcon."
)
FAILED_OUTPUT_MESSAGE: str = (
    "Error executing action 'CrowdStrike - List Uploaded IOCs'. Reason: "
    '"IOC Type Filter" contains an invalid value. Please check the spelling. '
    "Possible values: ipv4, ipv6, md5, sha256, domain."
)

INTEGRATION_CUSTOMER_ID: str = "integration_cid_for_iocs"

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
        parameters={
            **SUCCESS_PARAMS, "IOC Type Filter": "md5", "Value Filter String": "hash",
        },
        integration_config_file_path=CONFIG_PATH,
    )
    def test_list_uploaded_ioc_success(
        self,
        script_session: CrowdStrikeFalconSession,
        crowd_strike_falcon: CrowdStrikeFalcon,
        action_output: MockActionOutput,
    ) -> None:
        crowd_strike_falcon.add_entries(
            "custom_indicators",
            MOCK_DATA["iocs_entities_indicators_ids"]["resources"],
        )

        ListUploadedIOCs.main()

        assert len(script_session.request_history) == 3
        assert action_output.results.output_message == SUCCESS_OUTPUT_MESSAGE
        assert action_output.results.result_value == 1
        assert action_output.results.execution_state == ExecutionState.COMPLETED

    @set_metadata(
        parameters=FAILED_PARAMS,
        integration_config_file_path=CONFIG_PATH,
    )
    def test_list_uploaded_ioc_wrong_filter(
        self,
        script_session: CrowdStrikeFalconSession,
        action_output: MockActionOutput,
    ) -> None:
        ListUploadedIOCs.main()

        assert len(script_session.request_history) == 0
        assert action_output.results.output_message == FAILED_OUTPUT_MESSAGE
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
        script_session: CrowdStrikeFalconSession,
    ) -> None:
        """Verifies that 'member_cid' is not sent when the integration config
        does not contain a Customer ID.
        """
        ListUploadedIOCs.main()

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
        script_session: CrowdStrikeFalconSession,
    ) -> None:
        """Verifies that 'member_cid' is sent when the integration config
        contains a Customer ID.
        """
        ListUploadedIOCs.main()

        history_record: Any = script_session.request_history[0]
        token_request_payload: dict[str, Any] = history_record.request.kwargs.get(
            "data", {},
        )
        assert token_request_payload.get("member_cid") == INTEGRATION_CUSTOMER_ID
