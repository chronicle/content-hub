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

from typing import TYPE_CHECKING

import requests
from integration_testing.set_meta import set_metadata
from TIPCommon.base.action import ExecutionState

from sentinel_one_singularity_operations_center.actions import ping
from sentinel_one_singularity_operations_center.tests.common import CONFIG_PATH

if TYPE_CHECKING:
    import pytest
    from integration_testing.platform.script_output import MockActionOutput

    from sentinel_one_singularity_operations_center.tests.core.product import (
        SentinelOne,
    )
    from sentinel_one_singularity_operations_center.tests.core.session import (
        SentinelOneSession,
    )


class TestPing:
    @set_metadata(integration_config_file_path=CONFIG_PATH)
    def test_ping_success(
        self,
        script_session: SentinelOneSession,
        action_output: MockActionOutput,
        sentinelone: SentinelOne,
    ) -> None:
        success_output_msg = (
            "Successfully connected to the SentinelOne Singularity Operations Center server with "
            "the provided connection parameters!"
        )

        ping.main()

        assert len(script_session.request_history) == 1
        request = script_session.request_history[0].request
        assert request.url.path.endswith("/web/api/v2.1/unifiedalerts/graphql")

        assert action_output.results is not None
        assert action_output.results.output_message == success_output_msg
        assert action_output.results.execution_state == ExecutionState.COMPLETED

    @set_metadata(integration_config_file_path=CONFIG_PATH)
    def test_ping_failure(
        self,
        script_session: SentinelOneSession,
        action_output: MockActionOutput,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Test Ping action failure scenario when a network error occurs."""

        def mock_request_fail(*args: object, **kwargs: object) -> None:
            error_msg = "Connection refused"
            raise requests.exceptions.ConnectionError(error_msg)

        monkeypatch.setattr(script_session, "request", mock_request_fail)

        ping.main()

        assert action_output.results is not None
        assert action_output.results.execution_state == ExecutionState.FAILED
        expected_err_prefix = "Failed to connect to the SentinelOne Singularity Operations Center server! Error is"
        assert expected_err_prefix in action_output.results.output_message
        assert "Connection refused" in action_output.results.output_message
        assert action_output.results.result_value is False
