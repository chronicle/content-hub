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
import pathlib

from TIPCommon.base.action import ExecutionState
from TIPCommon.base.data_models import ActionOutput

from ..actions.Ping import (
    Ping,
    SUCCESS_MESSAGE,
    ERROR_MESSAGE,
)
import web_risk.core.WebRiskConstants as Constants

from ..tests.common import CONFIG
from ..tests.core.session import ApiSession
from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata


NO_CREDS_OUTPUT_MESSAGE = (
    f"{ERROR_MESSAGE}\nReason: No service account, workload identity "
    "email were provided, or missing mandatory fields for service account"
)
INVALID_EMAIL_OUTPUT_MESSAGE = (
    f"{ERROR_MESSAGE}\nReason: Impersonation is not allowed for the "
    "provided service account invalid-sa@domain.com. Please add the "
    "\"Service Account Token Creator\" role to the service account:"
)

CONFIG_WITHOUT_CREDS = CONFIG.copy()
CONFIG_WITHOUT_CREDS["Workload Identity Email"] = None

CONFIG_WITH_INVALID_EMAIL = CONFIG.copy()
CONFIG_WITH_INVALID_EMAIL["Workload Identity Email"] = "invalid-sa@domain.com"


class TestPing:

    @set_metadata(
        integration_config=CONFIG
    )
    def test_success(
            self,
            script_session: ApiSession,
            action_output: MockActionOutput,
    ) -> None:
        Ping(script_name=Constants.PING_SCRIPT_NAME).run()

        assert len(script_session.request_history) >= 2
        assert (
            script_session.request_history[-1].request.url.path
            == "/v1/uris:search"
        )
        assert action_output.results == ActionOutput(
            output_message=SUCCESS_MESSAGE,
            result_value=True,
            execution_state=ExecutionState.COMPLETED,
            json_output=None,
        )

    @set_metadata(
        integration_config=CONFIG_WITHOUT_CREDS
    )
    def test_without_creds(
            self,
            script_session: ApiSession,
            action_output: MockActionOutput,
    ) -> None:
        Ping(script_name=Constants.PING_SCRIPT_NAME).run()

        assert len(script_session.request_history) == 0
        assert action_output.results == ActionOutput(
            output_message=NO_CREDS_OUTPUT_MESSAGE,
            result_value=False,
            execution_state=ExecutionState.FAILED,
            json_output=None,
        )

    @set_metadata(
        integration_config=CONFIG_WITH_INVALID_EMAIL
    )
    def test_invalid_email(
            self,
            script_session: ApiSession,
            action_output: MockActionOutput,
    ) -> None:
        Ping(script_name=Constants.PING_SCRIPT_NAME).run()

        assert len(script_session.request_history) >= 1
        assert (
            script_session.request_history[-1]
            .response.json().get("error", {}).get("message")
            == "Not found; Gaia id not found for email invalid-sa@domain.com"
        )
        assert script_session.request_history[-1].response.status_code == 404
        assert INVALID_EMAIL_OUTPUT_MESSAGE in action_output.results.output_message
        assert action_output.results.result_value is False
        assert action_output.results.execution_state == ExecutionState.FAILED
        assert action_output.results.json_output is None
