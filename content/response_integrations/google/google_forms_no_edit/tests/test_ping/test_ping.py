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

from TIPCommon.base.action import ExecutionState
from TIPCommon.base.data_models import ActionOutput

from google_forms.actions.Ping import Ping
from google_forms.tests.common import CONFIG, CONFIG_PATH
from google_forms.tests.core.session import GoogleFormsSession
from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata


PING_SUCCESS_MESSAGE: str = (
    "Successfully connected to the Google Forms server with the provided"
    " connection parameters!"
)
MISSING_EMAIL_ERROR_MESSAGE: str = (
    "Failed to connect to the Google Forms server!\n"
    "Reason: Missing mandatory parameter Delegated Email"
)
MISSING_SERVICE_ACCOUNT_ERROR_MESSAGE: str = (
    "Failed to connect to the Google Forms server!\n"
    "Reason: Missing mandatory parameter Service Account JSON"
)
CONNECTIVITY_URL: str = "/admin/directory/v1/users"

CONFIG_WITHOUT_CREDS = CONFIG.copy()
CONFIG_WITHOUT_CREDS["Delegated Email"] = None

CONFIG_WITH_INVALID_EMAIL = CONFIG.copy()
CONFIG_WITH_INVALID_EMAIL["Service Account JSON"] = None


class TestPing:
    @set_metadata(integration_config_file_path=CONFIG_PATH)
    def test_success(
        self,
        script_session: GoogleFormsSession,
        action_output: MockActionOutput,
    ) -> None:

        Ping().run()

        assert len(script_session.request_history) == 1
        assert script_session.request_history[0].request.url.path == CONNECTIVITY_URL
        assert action_output.results == ActionOutput(
            output_message=PING_SUCCESS_MESSAGE,
            result_value=True,
            execution_state=ExecutionState.COMPLETED,
            json_output=None,
        )

    @set_metadata(integration_config=CONFIG_WITHOUT_CREDS)
    def test_empty_email_fail(
        self,
        script_session: GoogleFormsSession,
        action_output: MockActionOutput,
    ) -> None:

        Ping().run()

        assert len(script_session.request_history) == 0
        assert action_output.results == ActionOutput(
            output_message=MISSING_EMAIL_ERROR_MESSAGE,
            result_value=False,
            execution_state=ExecutionState.FAILED,
            json_output=None,
        )

    @set_metadata(integration_config=CONFIG_WITH_INVALID_EMAIL)
    def test_empty_service_account_fail(
        self,
        script_session: GoogleFormsSession,
        action_output: MockActionOutput,
    ) -> None:

        Ping().run()

        assert len(script_session.request_history) == 0
        assert action_output.results == ActionOutput(
            output_message=MISSING_SERVICE_ACCOUNT_ERROR_MESSAGE,
            result_value=False,
            execution_state=ExecutionState.FAILED,
            json_output=None,
        )
