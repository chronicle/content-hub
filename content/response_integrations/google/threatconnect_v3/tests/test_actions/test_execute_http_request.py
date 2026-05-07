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

"""Tests for Execute HTTP Request action."""

from __future__ import annotations

import pathlib
from typing import TYPE_CHECKING

from integration_testing.request import MockRequest
from integration_testing.requests.response import MockResponse
from integration_testing.set_meta import set_metadata
from TIPCommon.base.action import ExecutionState

if TYPE_CHECKING:
    from integration_testing.platform.script_output import MockActionOutput

from threatconnect_v3.actions import execute_http_request
from threatconnect_v3.tests.core.session import ThreatConnectV3Session

CONFIG_PATH = pathlib.Path(__file__).parent.parent / "config.json"


class TestExecuteHttpRequest:
    """Test cases for Execute HTTP Request action."""

    @set_metadata(
        parameters={
            "Method": "GET",
            "URL Path": "https://partners.threatconnect.com/api/v3/indicators?resultLimit=1",
            "Fields To Return": "response_data, response_code",
            "Request Timeout": "120",
        },
        integration_config_file_path=CONFIG_PATH,
    )
    def test_execute_http_request_success(
        self,
        script_session: ThreatConnectV3Session,
        action_output: MockActionOutput,
    ) -> None:
        """Test successful execution of HTTP request."""
        execute_http_request.main()

        assert len(script_session.request_history) == 1
        request = script_session.request_history[0].request
        assert (
            request.url.geturl()
            == "https://partners.threatconnect.com/api/v3/indicators?resultLimit=1"
        )
        assert request.method.value == "GET"

        assert action_output.results is not None
        assert (
            action_output.results.output_message
            == execute_http_request.SUCCESS_MESSAGE
        )
        assert action_output.results.execution_state == ExecutionState.COMPLETED

    @set_metadata(
        parameters={
            "Method": "GET",
            "URL Path": "https://partners.threatconnect.com/api/v3/indicators?resultLimit=1",
            "Fields To Return": "response_data, response_code",
            "Request Timeout": "120",
            "Fail on 4xx/5xx": "False",
        },
        integration_config_file_path=CONFIG_PATH,
    )
    def test_execute_http_request_failure_no_raise(
        self,
        script_session: ThreatConnectV3Session,
        action_output: MockActionOutput,
    ) -> None:
        """Test failed execution of HTTP request without raising exception."""

        def mock_get_indicators(request: MockRequest) -> MockResponse:
            return MockResponse(
                content={"message": "Unauthorized", "status": "Error"},
                status_code=401,
            )
        script_session.routes["GET"][r"/api/v3/indicators"] = mock_get_indicators  # type: ignore

        execute_http_request.main()

        assert len(script_session.request_history) == 1
        assert action_output.results is not None
        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert "status code 401 was returned" in action_output.results.output_message

    @set_metadata(
        parameters={
            "Method": "GET",
            "URL Path": "https://partners.threatconnect.com/api/v3/indicators?resultLimit=1",
            "Fields To Return": "response_data, response_code",
            "Request Timeout": "120",
            "Fail on 4xx/5xx": "True",
        },
        integration_config_file_path=CONFIG_PATH,
    )
    def test_execute_http_request_failure_raise(
        self,
        script_session: ThreatConnectV3Session,
        action_output: MockActionOutput,
    ) -> None:
        """Test failed execution of HTTP request with raising exception."""

        def mock_get_indicators(request: MockRequest) -> MockResponse:
            return MockResponse(
                content={"message": "Unauthorized", "status": "Error"},
                status_code=401,
            )
        script_session.routes["GET"][r"/api/v3/indicators"] = mock_get_indicators  # type: ignore

        execute_http_request.main()

        assert len(script_session.request_history) == 1
        assert action_output.results is not None
        assert action_output.results.execution_state == ExecutionState.FAILED

    @set_metadata(
        parameters={
            "Method": "POST",
            "URL Path": "https://partners.threatconnect.com/api/v3/indicators",
            "Body Payload": '{"type": "Address", "summary": "1.1.1.1"}',
            "Fields To Return": "response_data, response_code",
            "Request Timeout": "120",
        },
        integration_config_file_path=CONFIG_PATH,
    )
    def test_execute_http_request_post_body(
        self,
        script_session: ThreatConnectV3Session,
        action_output: MockActionOutput,
    ) -> None:
        """Test successful execution of POST request with body."""

        def mock_post_indicators(request: MockRequest) -> MockResponse:
            return MockResponse(
                content={"status": "success"},
                status_code=201,
            )
        script_session.routes["POST"][r"/api/v3/indicators"] = mock_post_indicators  # type: ignore

        execute_http_request.main()

        assert len(script_session.request_history) == 1
        request = script_session.request_history[0].request
        assert request.method.value == "POST"
        assert request.kwargs.get("data") == '{"type": "Address", "summary": "1.1.1.1"}'

    @set_metadata(
        parameters={
            "Method": "GET",
            "URL Path": "https://partners.threatconnect.com/api/v3/indicators",
            "URL Params": '{"resultLimit": "5"}',
            "Fields To Return": "response_data, response_code",
            "Request Timeout": "120",
        },
        integration_config_file_path=CONFIG_PATH,
    )
    def test_execute_http_request_url_params(
        self,
        script_session: ThreatConnectV3Session,
        action_output: MockActionOutput,
    ) -> None:
        """Test successful execution of GET request with URL params."""
        execute_http_request.main()

        assert len(script_session.request_history) == 1
        request = script_session.request_history[0].request
        assert request.kwargs.get("params") == {"resultLimit": "5"}
