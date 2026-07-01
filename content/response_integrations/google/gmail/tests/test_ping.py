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
import gmail.core.GoogleGmailConsts as Constants

from ..tests.common import CONFIG
from ..tests.core.session import GoogleGmailSession
from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata


NO_CREDS_OUTPUT_MESSAGE = (
    f"{ERROR_MESSAGE}\nReason: No service account or workload identity email were provided."
)
INVALID_EMAIL_OUTPUT_MESSAGE = (
    f"{ERROR_MESSAGE}\nReason: Impersonation is not allowed for the provided "
    "service account. Please check the \"Service Account Token Creator\" role to the "
    "service account: "
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
            gmail_script_session: GoogleGmailSession,
            action_output: MockActionOutput,
    ) -> None:
        action = Ping(script_name=Constants.PING_SCRIPT_NAME)
        action._is_first_run = True
        action.run()

        assert len(gmail_script_session.request_history) == 1
        assert (
            gmail_script_session.request_history[-1].request.url.path
            == "/o/oauth2/token"
        )
        assert action_output.results == ActionOutput(
            output_message=SUCCESS_MESSAGE,
            result_value=True,
            execution_state=ExecutionState.COMPLETED,
            json_output=None
        )

    @set_metadata(
        integration_config=CONFIG_WITHOUT_CREDS
    )
    def test_without_creds(
            self,
            gmail_script_session: GoogleGmailSession,
            action_output: MockActionOutput,
    ) -> None:
        action = Ping(script_name=Constants.PING_SCRIPT_NAME)
        action._is_first_run = True
        action.run()

        assert len(gmail_script_session.request_history) == 0
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
            gmail_script_session: GoogleGmailSession,
            action_output: MockActionOutput,
    ) -> None:
        action = Ping(script_name=Constants.PING_SCRIPT_NAME)
        action._is_first_run = True
        action.run()

        assert len(gmail_script_session.request_history) == 0
        assert INVALID_EMAIL_OUTPUT_MESSAGE in action_output.results.output_message
        assert action_output.results.result_value is False
        assert action_output.results.execution_state == ExecutionState.FAILED
        assert action_output.results.json_output is None
