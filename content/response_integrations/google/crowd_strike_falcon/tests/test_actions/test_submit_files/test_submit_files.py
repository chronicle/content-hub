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

import datetime
from typing import Any

import pytest
from crowd_strike_falcon.actions import SubmitFile
from TIPCommon.base.action import ExecutionState
from TIPCommon.types import SingleJson

from crowd_strike_falcon.tests.common import (
    CONFIG,
    CONFIG_PATH,
    MOCK_DATA,
    SUBMIT_FILE_PATH,
)
from crowd_strike_falcon.tests.core.crowd_strike_falcon import (
    CrowdStrikeFalcon,
)
from crowd_strike_falcon.tests.core.session import CrowdStrikeFalconSession
from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata

CHECK_DUPLICATE: bool = False
NETWORK_ENV: str = "Default"
SANDBOX_ENV: str = "Windows 10, 64-bit"

SUCCESS_OUTPUT_MESSAGE: str = (
    "Successfully returned details about the following files using Crowdstrike: "
    f"{SUBMIT_FILE_PATH}"
)
SCRIPT_DEADLINE_TIME: datetime.datetime = (
    datetime.datetime.now() + datetime.timedelta(minutes=10)
)
TIMEOUT: SingleJson = {
    "execution_deadline_unix_time_ms": int(
        SCRIPT_DEADLINE_TIME.timestamp() * 1000,
    ),
}

INTEGRATION_CUSTOMER_ID: str = "integration_cid_for_submit_file"
INTEGRATION_CONFIG_WITH_CID: SingleJson = CONFIG.copy()
INTEGRATION_CONFIG_WITH_CID["Customer ID"] = INTEGRATION_CUSTOMER_ID

BASE_PARAMS: SingleJson = {
    "File Paths": str(SUBMIT_FILE_PATH),
    "Sandbox Environment": SANDBOX_ENV,
    "Network Environment": NETWORK_ENV,
    "Archive Password": "",
    "Document Password": "",
    "Check Duplicate": CHECK_DUPLICATE,
    "Comment": "",
    "Confidential Submission": True,
}


@pytest.mark.usefixtures("script_session")
class TestHappyPath:

    @set_metadata(
        parameters=BASE_PARAMS,
        integration_config_file_path=CONFIG_PATH,
        input_context=TIMEOUT,
    )
    def test_submit_files_success(
        self,
        script_session: CrowdStrikeFalconSession,
        crowd_strike_falcon: CrowdStrikeFalcon,
        action_output: MockActionOutput,
    ) -> None:
        crowd_strike_falcon.add_file(
            MOCK_DATA["samples_entities_sample_v1"]["resources"],
        )

        SubmitFile.main(True)

        assert len(script_session.request_history) == 5
        assert action_output.results.output_message == SUCCESS_OUTPUT_MESSAGE
        assert action_output.results.result_value is True
        assert action_output.results.execution_state == ExecutionState.COMPLETED


@pytest.mark.usefixtures("script_session")
class TestTenantAuthentication:
    """Tests the tenant authentication logic based on integration configuration."""

    @set_metadata(
        parameters=BASE_PARAMS,
        integration_config_file_path=CONFIG_PATH,
        input_context=TIMEOUT,
    )
    def test_parent_tenant_auth_when_no_cid_in_config(
        self,
        script_session: CrowdStrikeFalconSession,
    ) -> None:
        """Verifies that 'member_cid' is not sent when the integration config
        does not contain a Customer ID.
        """
        SubmitFile.main(True)

        history_record: Any = script_session.request_history[0]
        token_request_payload: dict[str, Any] = history_record.request.kwargs.get(
            "data", {},
        )
        assert "member_cid" not in token_request_payload

    @set_metadata(
        parameters=BASE_PARAMS,
        integration_config=INTEGRATION_CONFIG_WITH_CID,
        input_context=TIMEOUT,
    )
    def test_child_tenant_auth_when_cid_is_in_config(
        self,
        script_session: CrowdStrikeFalconSession,
    ) -> None:
        """Verifies that 'member_cid' is sent when the integration config
        contains a Customer ID.
        """
        SubmitFile.main(True)

        history_record: Any = script_session.request_history[0]
        token_request_payload: dict[str, Any] = history_record.request.kwargs.get(
            "data", {},
        )
        assert token_request_payload.get("member_cid") == INTEGRATION_CUSTOMER_ID
