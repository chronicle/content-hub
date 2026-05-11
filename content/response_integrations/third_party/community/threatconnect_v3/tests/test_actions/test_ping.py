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

"""Tests for Ping action."""

from __future__ import annotations

import pathlib
from typing import TYPE_CHECKING

from integration_testing.requests.response import MockResponse
from integration_testing.set_meta import set_metadata
from TIPCommon.base.action import ExecutionState

if TYPE_CHECKING:
    from integration_testing.platform.script_output import MockActionOutput
    from integration_testing.request import MockRequest

    from threatconnect_v3.tests.core.session import ThreatConnectV3Session

from threatconnect_v3.actions import ping

CONFIG_PATH = pathlib.Path(__file__).parent.parent / "config.json"


class TestPing:
    """Test cases for Ping action."""

    @set_metadata(
        parameters={},
        integration_config_file_path=CONFIG_PATH,
    )
    def test_ping_success(
        self,
        script_session: ThreatConnectV3Session,
        action_output: MockActionOutput,
    ) -> None:
        """Test successful execution of Ping action."""
        ping.main()

        assert len(script_session.request_history) == 1
        request = script_session.request_history[0].request
        assert request.url.path.endswith("/api/v3/indicators")
        assert request.method.value == "GET"

        assert action_output.results is not None
        assert action_output.results.output_message == ping.SUCCESS_MESSAGE
        assert action_output.results.execution_state == ExecutionState.COMPLETED

    @set_metadata(
        parameters={},
        integration_config_file_path=CONFIG_PATH,
    )
    def test_ping_failure(
        self,
        script_session: ThreatConnectV3Session,
        action_output: MockActionOutput,
    ) -> None:
        """Test failed execution of Ping action."""

        # Override route to return 401
        def mock_get_indicators(request: MockRequest) -> MockResponse:
            return MockResponse(
                content={"message": "Unauthorized", "status": "Error"},
                status_code=401,
            )
        script_session.routes["GET"][r"/api/v3/indicators"] = mock_get_indicators

        ping.main()

        assert len(script_session.request_history) == 1
        assert action_output.results is not None
        assert action_output.results.execution_state == ExecutionState.FAILED
        assert "Failed to connect" in action_output.results.output_message
