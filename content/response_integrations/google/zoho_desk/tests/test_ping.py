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

from zoho_desk.actions.Ping import Ping
from zoho_desk.tests.common import (
    ACCESS_TOKEN_DB_ROW,
    CONFIG_PATH,
    EXPIRED_ACCESS_TOKEN_DB_ROW,
)
from zoho_desk.tests.core.session import ZohoDeskSession
from integration_testing.platform.external_context import MockExternalContext
from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata


SUCCESS_OUTPUT_MESSAGE = (
    "Successfully connected to the Zoho Desk server with the provided connection "
    "parameters!"
)
FAILURE_OUTPUT_MESSAGE = (
    'Error executing action "Zoho Desk - Ping"\n'
    "Reason: Unable to obtain access token: 400 Client Error: None for url: None - "
    "[{'errorMessage': 'Wrong Credentials!'}]"
)


class TestHappyPath:

    @set_metadata(
        external_context=MockExternalContext(ACCESS_TOKEN_DB_ROW),
        integration_config_file_path=CONFIG_PATH
    )
    def test_ping_with_oauth_in_db_does_not_creates_new_oauth_token(
        self,
        script_session: ZohoDeskSession,
        action_output: MockActionOutput,
    ) -> None:
        Ping().run()

        assert len(script_session.request_history) == 1
        assert script_session.request_history[0].request.url.path == "/api/v1/agents"
        assert action_output.results == ActionOutput(
            output_message=SUCCESS_OUTPUT_MESSAGE,
            result_value=True,
            execution_state=ExecutionState.COMPLETED,
            json_output=None,
        )


class TestError:

    @set_metadata(
        integration_config={
            "API Root": "raise_error",
            "Client ID": "raise_error",
            "Client Secret": "raise_error",
            "Refresh Token": "raise_error",
            "Verify SSL": True
        }
    )
    def test_ping_with_oauth_in_db_does_not_creates_new_oauth_token(
        self,
        script_session: ZohoDeskSession,
        action_output: MockActionOutput,
    ) -> None:
        Ping().run()

        assert len(script_session.request_history) == 1
        assert script_session.request_history[0].request.url.path == "/oauth/v2/token"
        assert script_session.request_history[0].response.status_code == 400
        assert action_output.results == ActionOutput(
            output_message=FAILURE_OUTPUT_MESSAGE,
            result_value=False,
            execution_state=ExecutionState.FAILED,
            json_output=None,
        )


class TestOauthToken:

    @set_metadata(integration_config_file_path=CONFIG_PATH)
    def test_ping_without_oauth_in_db_creates_new_oauth_token(
        self,
        script_session: ZohoDeskSession,
        action_output: MockActionOutput,
    ) -> None:
        Ping().run()

        assert len(script_session.request_history) == 2
        assert script_session.request_history[0].request.url.path == "/oauth/v2/token"
        assert script_session.request_history[1].request.url.path == "/api/v1/agents"
        assert action_output.results == ActionOutput(
            output_message=SUCCESS_OUTPUT_MESSAGE,
            result_value=True,
            execution_state=ExecutionState.COMPLETED,
            json_output=None,
        )

    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        external_context=MockExternalContext(EXPIRED_ACCESS_TOKEN_DB_ROW)
    )
    def test_ping_with_expired_oauth_in_db_creates_new_oauth_token(
        self,
        script_session: ZohoDeskSession,
        action_output: MockActionOutput,
    ) -> None:
        Ping().run()

        assert len(script_session.request_history) == 2
        assert script_session.request_history[0].request.url.path == "/oauth/v2/token"
        assert script_session.request_history[1].request.url.path == "/api/v1/agents"
        assert action_output.results == ActionOutput(
            output_message=SUCCESS_OUTPUT_MESSAGE,
            result_value=True,
            execution_state=ExecutionState.COMPLETED,
            json_output=None,
        )
