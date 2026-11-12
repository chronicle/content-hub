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

import json
import pathlib

from TIPCommon.base.action import ExecutionState
from TIPCommon.base.data_models import ActionOutput, ActionJsonOutput
from TIPCommon.types import SingleJson

from google_cloud_api.actions.ExecuteHTTPRequest import (
    ExecuteHttpRequest,
    SUCCESS_MESSAGE,
    ERROR_MESSAGE,
)
import google_cloud_api.core.GoogleCloudApiConstants as Constants

from google_cloud_api.tests.common import CONFIG
from google_cloud_api.tests.core.session import GoogleCloudApiSession
from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata
from integration_testing.common import get_def_file_content
from integration_testing.request import HttpMethod

SUCCESS_OUTPUT_WITH_ERROR = (
    "Successfully executed API request, but the status code 400 was returned. "
    "Please check the request or try again later."
)
NO_CREDS_OUTPUT_MESSAGE = (
    f"{ERROR_MESSAGE}\nReason: No service account, workload identity "
    "email were provided, or missing mandatory fields for service account"
)
INVALID_EMAIL_OUTPUT_MESSAGE = (
    f"{ERROR_MESSAGE}\nReason: Impersonation is not allowed for the "
    "provided service account invalid-sa@domain.com. Please add the "
    "\"Service Account Token Creator\" role to the service account:"
)
POST_ERROR_MESSAGE = (
    f"{ERROR_MESSAGE}\nReason: An error occurred: 400 Client Error: "
    "None for url: None {}"
)

CONFIG_WITHOUT_CREDS = CONFIG.copy()
CONFIG_WITHOUT_CREDS["Workload Identity Email"] = None

CONFIG_WITH_INVALID_EMAIL = CONFIG.copy()
CONFIG_WITH_INVALID_EMAIL["Workload Identity Email"] = "invalid-sa@domain.com"

ACTION_CONFIG_PATH: pathlib.Path = pathlib.Path(__file__).parent / "config.json"
ACTION_CONFIG: SingleJson = get_def_file_content(ACTION_CONFIG_PATH)

ACTION_CONFIG_POST = ACTION_CONFIG.copy()
ACTION_CONFIG_POST["URL Path"] = "https://example.com/post_error"
ACTION_CONFIG_POST["Method"] = "POST"
ACTION_CONFIG_POST["Body Payload"] = "{\"test_body_field\": \"test_body_value\"}"

ACTION_CONFIG_POST_RECURSIVE = ACTION_CONFIG.copy()
ACTION_CONFIG_POST_RECURSIVE["URL Path"] = "https://example.com/post_valid"
ACTION_CONFIG_POST_RECURSIVE["Method"] = "POST"
ACTION_CONFIG_POST_RECURSIVE["Body Payload"] = (
    "{\"test_body_field\": [\"test_body_value\", {\"child_key\": \"child_value\"}]}"
)

ACTION_CONFIG_POST_NOT_FAIL_ON_ERROR = ACTION_CONFIG_POST.copy()
ACTION_CONFIG_POST_NOT_FAIL_ON_ERROR["Fail on 4xx/5xx"] = "false"


class TestExecuteHttpRequestAuth:

    @set_metadata(
        integration_config=CONFIG_WITHOUT_CREDS,
        parameters=ACTION_CONFIG,
    )
    def test_without_creds(
            self,
            gcloud_api_script_session: GoogleCloudApiSession,
            action_output: MockActionOutput,
    ) -> None:
        ExecuteHttpRequest(script_name=Constants.PING_SCRIPT_NAME).run()

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
        ExecuteHttpRequest(script_name=Constants.PING_SCRIPT_NAME).run()

        assert len(gcloud_api_script_session.request_history) >= 2
        assert (
            gcloud_api_script_session.request_history[-1]
            .response.json().get("error", {}).get("message")
            == "Not found; Gaia id not found for email invalid-sa@domain.com"
        )
        assert gcloud_api_script_session.request_history[-1].response.status_code == 404
        assert INVALID_EMAIL_OUTPUT_MESSAGE in action_output.results.output_message
        assert action_output.results.result_value is False
        assert action_output.results.execution_state == ExecutionState.FAILED
        assert action_output.results.json_output is None


class TestExecuteHttpRequestGet:

    @set_metadata(
        integration_config=CONFIG,
        parameters=ACTION_CONFIG,
    )
    def test_get_test_resource(
            self,
            gcloud_api_script_session: GoogleCloudApiSession,
            action_output: MockActionOutput,
    ) -> None:
        ExecuteHttpRequest(script_name=Constants.EXECUTE_HTTP_REQUEST_SCRIPT_NAME).run()

        assert len(gcloud_api_script_session.request_history) >= 3
        assert (
            gcloud_api_script_session.request_history[-1].request.method
            == HttpMethod.GET
        )
        assert (
            gcloud_api_script_session.request_history[-1].request.url.path
            == "/get_test_resource"
        )
        assert (
            gcloud_api_script_session.request_history[-1].request.kwargs["params"] ==
            json.loads(ACTION_CONFIG["URL Params"])
        )
        assert (
            gcloud_api_script_session.request_history[-1].request.kwargs["headers"] ==
            json.loads(ACTION_CONFIG["Headers"])
        )
        assert action_output.results == ActionOutput(
            output_message=SUCCESS_MESSAGE,
            result_value=True,
            execution_state=ExecutionState.COMPLETED,
            json_output=ActionJsonOutput(
                json_result={
                    "response_data": {"name": "test-resource"},
                    "redirects": [None],
                    "response_code": 200,
                    "response_cookies": {},
                    "response_headers": {},
                    "apparent_encoding": "ascii"
                }
            ),
        )


class TestExecuteRequestPost:
    @set_metadata(
        integration_config=CONFIG,
        parameters=ACTION_CONFIG_POST_RECURSIVE,
    )
    def test_post_valid(
            self,
            gcloud_api_script_session: GoogleCloudApiSession,
            action_output: MockActionOutput,
    ) -> None:
        ExecuteHttpRequest(script_name=Constants.EXECUTE_HTTP_REQUEST_SCRIPT_NAME).run()

        assert len(gcloud_api_script_session.request_history) >= 3
        assert (
            gcloud_api_script_session.request_history[-1].request.method
            == HttpMethod.POST
        )
        assert (
            gcloud_api_script_session.request_history[-1].request.url.path
            == "/post_valid"
        )
        assert (
            gcloud_api_script_session.request_history[-1].request.kwargs["params"]
            == json.loads(ACTION_CONFIG_POST_RECURSIVE["URL Params"])
        )
        assert (
            gcloud_api_script_session.request_history[-1].request.kwargs["headers"]
            == json.loads(ACTION_CONFIG_POST_RECURSIVE["Headers"])
        )
        assert (
            gcloud_api_script_session.request_history[-1].request.kwargs["json"] ==
            json.loads(ACTION_CONFIG_POST_RECURSIVE["Body Payload"])
        )
        assert action_output.results == ActionOutput(
            output_message=SUCCESS_MESSAGE,
            result_value=True,
            execution_state=ExecutionState.COMPLETED,
            json_output=ActionJsonOutput(
                json_result={
                    "response_data": (
                        gcloud_api_script_session.request_history[-1].response.json()
                    ),
                    "redirects": [None],
                    "response_code": 200,
                    "response_cookies": {},
                    "response_headers": {},
                    "apparent_encoding": "ascii"
                }
            ),
        )

    @set_metadata(
        integration_config=CONFIG,
        parameters=ACTION_CONFIG_POST,
    )
    def test_post_error_with_fail(
            self,
            gcloud_api_script_session: GoogleCloudApiSession,
            action_output: MockActionOutput,
    ) -> None:
        ExecuteHttpRequest(script_name=Constants.EXECUTE_HTTP_REQUEST_SCRIPT_NAME).run()

        assert len(gcloud_api_script_session.request_history) >= 3
        assert (
            gcloud_api_script_session.request_history[-1].request.method
            == HttpMethod.POST
        )
        assert (
            gcloud_api_script_session.request_history[-1].request.url.path
            == "/post_error"
        )
        assert (
            gcloud_api_script_session.request_history[-1].request.kwargs["params"] ==
            json.loads(ACTION_CONFIG_POST["URL Params"])
        )
        assert (
            gcloud_api_script_session.request_history[-1].request.kwargs["headers"] ==
            json.loads(ACTION_CONFIG_POST["Headers"])
        )
        assert (
            gcloud_api_script_session.request_history[-1].request.kwargs["json"] ==
            json.loads(ACTION_CONFIG_POST["Body Payload"])
        )
        assert action_output.results == ActionOutput(
            output_message=POST_ERROR_MESSAGE.format(
                gcloud_api_script_session.request_history[-1].response.content
            ),
            result_value=False,
            execution_state=ExecutionState.FAILED,
            json_output=ActionJsonOutput(
                json_result={
                    "response_data": (
                        gcloud_api_script_session.request_history[-1].response.json()
                    ),
                    "redirects": [None],
                    "response_code": 400,
                    "response_cookies": {},
                    "response_headers": {},
                    "apparent_encoding": "ascii"
                }
            ),
        )

    @set_metadata(
        integration_config=CONFIG,
        parameters=ACTION_CONFIG_POST_NOT_FAIL_ON_ERROR,
    )
    def test_post_error_without_fail(
            self,
            gcloud_api_script_session: GoogleCloudApiSession,
            action_output: MockActionOutput,
    ) -> None:
        ExecuteHttpRequest(script_name=Constants.EXECUTE_HTTP_REQUEST_SCRIPT_NAME).run()

        assert len(gcloud_api_script_session.request_history) >= 3
        assert (
            gcloud_api_script_session.request_history[-1].request.method
            == HttpMethod.POST
        )
        assert (
            gcloud_api_script_session.request_history[-1].request.url.path
            == "/post_error"
        )
        assert (
            gcloud_api_script_session.request_history[-1].request.kwargs["params"] ==
            json.loads(ACTION_CONFIG_POST_NOT_FAIL_ON_ERROR["URL Params"])
        )
        assert (
            gcloud_api_script_session.request_history[-1].request.kwargs["headers"] ==
            json.loads(ACTION_CONFIG_POST_NOT_FAIL_ON_ERROR["Headers"])
        )
        assert (
            gcloud_api_script_session.request_history[-1].request.kwargs["json"] ==
            json.loads(ACTION_CONFIG_POST_NOT_FAIL_ON_ERROR["Body Payload"])
        )
        assert action_output.results == ActionOutput(
            output_message=SUCCESS_OUTPUT_WITH_ERROR,
            result_value=True,
            execution_state=ExecutionState.COMPLETED,
            json_output=ActionJsonOutput(
                json_result={
                    "response_data": (
                        gcloud_api_script_session.request_history[-1].response.json()
                    ),
                    "redirects": [None],
                    "response_code": 400,
                    "response_cookies": {},
                    "response_headers": {},
                    "apparent_encoding": "ascii"
                }
            ),
        )
