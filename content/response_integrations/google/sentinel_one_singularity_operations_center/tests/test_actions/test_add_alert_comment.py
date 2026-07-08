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

from typing import TYPE_CHECKING, Any, Never

from integration_testing.set_meta import set_metadata
from TIPCommon.base.action import ExecutionState

from sentinel_one_singularity_operations_center.actions import add_alert_comment
from sentinel_one_singularity_operations_center.core.api.api_client import (
    SentinelOneSingularityOperationsCenterApiClient,
)
from sentinel_one_singularity_operations_center.core.exceptions import (
    SentinelOneSingularityOperationsCenterError,
)
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


class TestAddAlertComment:
    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        parameters={
            "Alert ID": "019d114e-e4f4-7ad6-82c3-9829b6d0a801",
            "Comment": "This is a test comment",
            "Comment Type": "Plain Text",
        },
    )
    def test_add_alert_comment_success(
        self,
        script_session: SentinelOneSession,
        action_output: MockActionOutput,
        sentinelone: SentinelOne,
    ) -> None:
        alert_id = "019d114e-e4f4-7ad6-82c3-9829b6d0a801"

        add_alert_comment.main()

        # Should make 1 request: GraphQL AddAlertNote mutation
        assert len(script_session.request_history) == 1

        # Verify request is POST GraphQL Mutation
        req = script_session.request_history[0].request
        assert req.method.value == "POST"
        assert req.url.path.endswith("/web/api/v2.1/unifiedalerts/graphql")

        assert action_output.results is not None
        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert action_output.results.result_value is True
        assert (
            f"Successfully added comment to SentinelOne alert '{alert_id}'."
            in action_output.results.output_message
        )

    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        parameters={
            "Alert ID": "019d114e-e4f4-7ad6-82c3-9829b6d0a801",
            "Comment": "This is a markdown comment",
            "Comment Type": "Markdown",
        },
    )
    def test_add_alert_comment_success_markdown(
        self,
        script_session: SentinelOneSession,
        action_output: MockActionOutput,
        sentinelone: SentinelOne,
    ) -> None:
        alert_id = "019d114e-e4f4-7ad6-82c3-9829b6d0a801"

        add_alert_comment.main()

        # Should make 1 request: GraphQL AddAlertNote mutation
        assert len(script_session.request_history) == 1

        # Verify request is POST GraphQL Mutation
        req = script_session.request_history[0].request
        assert req.method.value == "POST"
        assert req.url.path.endswith("/web/api/v2.1/unifiedalerts/graphql")

        assert action_output.results is not None
        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert action_output.results.result_value is True
        assert (
            f"Successfully added comment to SentinelOne alert '{alert_id}'."
            in action_output.results.output_message
        )

    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        parameters={
            "Alert ID": "019d114e-e4f4-7ad6-82c3-9829b6d0a801",
            "Comment": "This comment should fail to add",
        },
    )
    def test_add_alert_comment_failure(
        self,
        monkeypatch: pytest.MonkeyPatch,
        action_output: MockActionOutput,
    ) -> None:
        alert_id = "019d114e-e4f4-7ad6-82c3-9829b6d0a801"

        def mock_add_comment_raise(*args: Any, **kwargs: Any) -> Never:  # noqa: ANN401
            msg = "API Connection error"
            raise SentinelOneSingularityOperationsCenterError(msg)

        monkeypatch.setattr(
            SentinelOneSingularityOperationsCenterApiClient,
            "add_alert_comment",
            mock_add_comment_raise,
        )

        add_alert_comment.main()

        assert action_output.results is not None
        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert action_output.results.result_value is False
        assert (
            f"Failed to add comment to SentinelOne alert '{alert_id}': API Connection error"
            in action_output.results.output_message
        )
