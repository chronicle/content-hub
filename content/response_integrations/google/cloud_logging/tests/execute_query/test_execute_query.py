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
from TIPCommon.base.data_models import ActionOutput, ActionJsonOutput
from TIPCommon.types import SingleJson

from ...actions.ExecuteQuery import ExecuteQuery

from ...tests.common import CONFIG
from ...tests.core.session import GoogleCloudApiSession
from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata
from integration_testing.common import get_def_file_content


NO_CREDS_OUTPUT_MESSAGE = (
    'Error executing action "Execute Query".\nReason: No service account,'
    " workload identity "
    "email were provided, or missing mandatory fields for service account"
)

INVALID_MAX_VALUE_OUTPUT_MESSAGE = (
    'Error executing action "Execute Query".\nReason: Invalid parameter '
    '"Max Records To Return". The value can\'t be lower then 1. '
    "Wrong value provided: -1"
)

INVALID_TIME_FRAME_OUTPUT_MESSAGE = (
    'Error executing action "Execute Query".\nReason: Invalid parameter "Time Frame". '
    "The provided value must be one of the following: "
    "last hour,last 6 hours,last 24 hours,last week,last month,custom. "
    "Wrong value provided: Select One"
)

INVALID_EMAIL_OUTPUT_MESSAGE = (
    "\nReason: Impersonation is not allowed for the "
    "provided service account invalid-sa@domain.com. Please add the "
    '"Service Account Token Creator" role to the service account:'
)

JSON_RESULT_PATH = pathlib.Path(
    pathlib.Path(__file__).parent.parent / "core" / "mock_data.json"
)
JSON_RESULT = get_def_file_content(JSON_RESULT_PATH)
JSON_RESULT = JSON_RESULT["get_from_project"]["content"]["entries"]

CONFIG_WITHOUT_CREDS = CONFIG.copy()
CONFIG_WITHOUT_CREDS["Workload Identity Email"] = None

CONFIG_WITH_INVALID_EMAIL = CONFIG.copy()
CONFIG_WITH_INVALID_EMAIL["Workload Identity Email"] = "invalid-sa@domain.com"

ACTION_CONFIG_PATH: pathlib.Path = pathlib.Path(__file__).parent / "config.json"
ACTION_CONFIG: SingleJson = get_def_file_content(ACTION_CONFIG_PATH)


ACTION_CONFIG_INVALID_MAX = ACTION_CONFIG.copy()
ACTION_CONFIG_INVALID_MAX["Max Records To Return"] = -1


ACTION_CONFIG_INVALID_TIME_FRAME = ACTION_CONFIG.copy()
ACTION_CONFIG_INVALID_TIME_FRAME["Time Frame"] = "Select One"


class TestExecuteQuery:

    @set_metadata(
        integration_config=CONFIG_WITHOUT_CREDS,
        parameters=ACTION_CONFIG,
    )
    def test_without_creds(
        self,
        gcloud_api_script_session: GoogleCloudApiSession,
        action_output: MockActionOutput,
    ) -> None:
        ExecuteQuery().run()
        assert len(gcloud_api_script_session.request_history) == 0
        assert action_output.results == ActionOutput(
            output_message=NO_CREDS_OUTPUT_MESSAGE,
            result_value=False,
            execution_state=ExecutionState.FAILED,
            json_output=None,
        )

    @set_metadata(
        integration_config=CONFIG_WITH_INVALID_EMAIL,
        parameters=ACTION_CONFIG,
    )
    def test_invalid_email(
        self,
        gcloud_api_script_session: GoogleCloudApiSession,
        action_output: MockActionOutput,
    ) -> None:
        ExecuteQuery().run()

        assert len(gcloud_api_script_session.request_history) >= 1

        token_request = next(req for req in reversed(gcloud_api_script_session.request_history) if "generateAccessToken" in req.request.url.path)
        
        assert (
            token_request
            .response.json()
            .get("error", {})
            .get("message")
            == "Not found; Gaia id not found for email invalid-sa@domain.com"
        )
        assert token_request.response.status_code == 404
        assert INVALID_EMAIL_OUTPUT_MESSAGE in action_output.results.output_message
        assert action_output.results.result_value is False
        assert action_output.results.execution_state == ExecutionState.FAILED
        assert action_output.results.json_output is None

    @set_metadata(
        integration_config=CONFIG,
        parameters=ACTION_CONFIG,
    )
    def test_proper_run(
        self,
        gcloud_api_script_session: GoogleCloudApiSession,
        action_output: MockActionOutput,
    ) -> None:
        ExecuteQuery().run()
        message = (
            f"Successfully executed query \"{ACTION_CONFIG['Query']} "
            "AND timestamp >= \"2024-10-23T11:46:46.549337+00:00\" AND "
            "timestamp <= \"2024-10-24T11:46:46.549337+00:00\"\""
            " in Cloud Logging"
        )
        assert len(gcloud_api_script_session.request_history) >= 2
        assert (
            gcloud_api_script_session.request_history[-1].request.kwargs["json"][
                "pageSize"
            ]
            == 2
        )
        assert action_output.results == ActionOutput(
            output_message=message,
            result_value=True,
            execution_state=ExecutionState.COMPLETED,
            json_output=ActionJsonOutput(json_result=JSON_RESULT),
        )

    @set_metadata(
        integration_config=CONFIG,
        parameters=ACTION_CONFIG_INVALID_MAX,
    )
    def test_invalid_max_value(
        self,
        gcloud_api_script_session: GoogleCloudApiSession,
        action_output: MockActionOutput,
    ) -> None:
        ExecuteQuery().run()

        assert len(gcloud_api_script_session.request_history) >= 1
        assert action_output.results == ActionOutput(
            output_message=INVALID_MAX_VALUE_OUTPUT_MESSAGE,
            result_value=False,
            execution_state=ExecutionState.FAILED,
            json_output=None,
        )

    @set_metadata(
        integration_config=CONFIG,
        parameters=ACTION_CONFIG_INVALID_TIME_FRAME,
    )
    def test_invalid_time_frame(
        self,
        gcloud_api_script_session: GoogleCloudApiSession,
        action_output: MockActionOutput,
    ) -> None:
        ExecuteQuery().run()

        assert len(gcloud_api_script_session.request_history) >= 1
        assert action_output.results == ActionOutput(
            output_message=INVALID_TIME_FRAME_OUTPUT_MESSAGE,
            result_value=False,
            execution_state=ExecutionState.FAILED,
            json_output=None,
        )
