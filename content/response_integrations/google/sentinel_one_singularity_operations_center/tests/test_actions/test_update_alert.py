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

from integration_testing.set_meta import set_metadata
from TIPCommon.base.action import ExecutionState

from sentinel_one_singularity_operations_center.actions import update_alert
from sentinel_one_singularity_operations_center.tests.common import CONFIG_PATH

if TYPE_CHECKING:
    from integration_testing.platform.script_output import MockActionOutput

    from sentinel_one_singularity_operations_center.tests.core.product import (
        SentinelOne,
    )
    from sentinel_one_singularity_operations_center.tests.core.session import (
        SentinelOneSession,
    )


class TestUpdateAlert:
    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        parameters={
            "Alert ID": "019d114e-e4f4-7ad6-82c3-9829b6d0a801",
            "Status": "Resolved",
            "Verdict": "True positive/Malware",
            "Assignee": "analyst@company.com",
        },
    )
    def test_update_alert_success(
        self,
        script_session: SentinelOneSession,
        action_output: MockActionOutput,
        sentinelone: SentinelOne,
    ) -> None:
        alert_id = "019d114e-e4f4-7ad6-82c3-9829b6d0a801"

        update_alert.main()

        # Should make 2 requests: 1. REST User Lookup, 2. GraphQL Update Alert
        assert len(script_session.request_history) == 2

        # Verify first request is GET /web/api/v2.1/users?email=analyst@company.com
        req_0 = script_session.request_history[0].request
        assert req_0.method.value == "GET"
        assert req_0.url.path.endswith("/web/api/v2.1/users")
        assert req_0.kwargs.get("params", {}).get("email") == "analyst@company.com"

        # Verify second request is POST GraphQL Mutation
        req_1 = script_session.request_history[1].request
        assert req_1.method.value == "POST"
        assert req_1.url.path.endswith("/web/api/v2.1/unifiedalerts/graphql")

        # Verify that the mock product database was actually updated with resolved ID
        assert sentinelone.details[alert_id]["status"] == "RESOLVED"
        assert (
            sentinelone.details[alert_id]["analystVerdict"] == "TRUE_POSITIVE_MALWARE"
        )
        assert sentinelone.details[alert_id]["assignee"] is not None
        assert sentinelone.details[alert_id]["assignee"]["userId"] == "98765"

        assert action_output.results is not None
        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert action_output.results.result_value is True
        assert (
            f"Successfully updated SentinelOne alert '{alert_id}'"
            in action_output.results.output_message
        )
        assert "Status to 'Resolved'" in action_output.results.output_message
        assert (
            "Verdict to 'True positive/Malware'" in action_output.results.output_message
        )
        assert (
            "Assignee to 'analyst@company.com'" in action_output.results.output_message
        )

    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        parameters={
            "Alert ID": "019d114e-e4f4-7ad6-82c3-9829b6d0a801",
            "Status": "Resolved",
            "Verdict": "True positive/Malware",
            "Assignee": "98765",
        },
    )
    def test_update_alert_success_direct_id(
        self,
        script_session: SentinelOneSession,
        action_output: MockActionOutput,
        sentinelone: SentinelOne,
    ) -> None:
        alert_id = "019d114e-e4f4-7ad6-82c3-9829b6d0a801"

        update_alert.main()

        # Should bypass REST lookup and make exactly 1 request (GraphQL Update)
        assert len(script_session.request_history) == 1
        req_0 = script_session.request_history[0].request
        assert req_0.method.value == "POST"
        assert req_0.url.path.endswith("/web/api/v2.1/unifiedalerts/graphql")

        # Verify that the mock product database was updated directly
        assert sentinelone.details[alert_id]["assignee"] is not None
        assert sentinelone.details[alert_id]["assignee"]["userId"] == "98765"

        assert action_output.results is not None
        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert action_output.results.result_value is True
        assert "Assignee to '98765'" in action_output.results.output_message

    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        parameters={
            "Alert ID": "019d114e-e4f4-7ad6-82c3-9829b6d0a801",
            "Status": "Resolved",
            "Verdict": "True positive/Malware",
            "Assignee": "not_found@company.com",
        },
    )
    def test_update_alert_user_not_found(
        self,
        script_session: SentinelOneSession,
        action_output: MockActionOutput,
        sentinelone: SentinelOne,
    ) -> None:
        update_alert.main()

        # Should attempt lookup and fail before calling GraphQL mutation
        assert len(script_session.request_history) == 1
        req_0 = script_session.request_history[0].request
        assert req_0.method.value == "GET"
        assert req_0.url.path.endswith("/web/api/v2.1/users")

        assert action_output.results is not None
        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert action_output.results.result_value is False
        assert (
            "User with email 'not_found@company.com' was not found in SentinelOne"
            in action_output.results.output_message
        )

    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        parameters={
            "Alert ID": "019d114e-e4f4-7ad6-82c3-9829b6d0a801",
            "Status": "New",
            "Verdict": "",
            "Assignee": "Unassign",
        },
    )
    def test_update_alert_unassign(
        self,
        script_session: SentinelOneSession,
        action_output: MockActionOutput,
        sentinelone: SentinelOne,
    ) -> None:
        alert_id = "019d114e-e4f4-7ad6-82c3-9829b6d0a801"

        update_alert.main()

        # Unassign bypasses REST lookup and makes exactly 1 request (GraphQL Update)
        assert len(script_session.request_history) == 1
        assert sentinelone.details[alert_id]["status"] == "NEW"
        assert sentinelone.details[alert_id]["assignee"] is None

        assert action_output.results is not None
        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert action_output.results.result_value is True
        assert (
            f"Successfully updated SentinelOne alert '{alert_id}'"
            in action_output.results.output_message
        )
        assert "Status to 'New'" in action_output.results.output_message
        assert "Assignee to 'Unassign'" in action_output.results.output_message

    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        parameters={
            "Alert ID": "019d114e-e4f4-7ad6-82c3-9829b6d0a801",
            "Status": "",
            "Verdict": "",
            "Assignee": "",
        },
    )
    def test_update_alert_no_params(
        self,
        script_session: SentinelOneSession,
        action_output: MockActionOutput,
        sentinelone: SentinelOne,
    ) -> None:
        update_alert.main()

        # No API request should be made because of validation failure
        assert len(script_session.request_history) == 0

        assert action_output.results is not None
        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert action_output.results.result_value is False
        assert "At least one update parameter" in action_output.results.output_message

    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        parameters={
            "Alert ID": "019d114e-e4f4-7ad6-82c3-9829b6d0a801",
            "Status": "Resolved",
            "Verdict": "",
            "Assignee": "invalid_username",
        },
    )
    def test_update_alert_invalid_assignee(
        self,
        script_session: SentinelOneSession,
        action_output: MockActionOutput,
        sentinelone: SentinelOne,
    ) -> None:
        update_alert.main()

        # No API request should be made because of validation failure
        assert len(script_session.request_history) == 0

        assert action_output.results is not None
        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert action_output.results.result_value is False
        assert (
            "Assignee parameter must be an email address, a numerical User ID, or 'Unassign'"
            in action_output.results.output_message
        )

    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        parameters={
            "Alert ID": "00000000-0000-0000-0000-000000000000",
            "Status": "Resolved",
            "Verdict": "",
            "Assignee": "",
        },
    )
    def test_update_alert_not_found(
        self,
        script_session: SentinelOneSession,
        action_output: MockActionOutput,
        sentinelone: SentinelOne,
    ) -> None:
        alert_id = "00000000-0000-0000-0000-000000000000"

        update_alert.main()

        assert len(script_session.request_history) == 1
        assert action_output.results is not None
        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert action_output.results.result_value is False
        assert (
            f"Error executing action \"Update Alert\". Reason: alert with ID {alert_id} wasn't found in SentinelOne Singularity Operations Center. Please check the spelling."
            in action_output.results.output_message
        )

    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        parameters={
            "Alert ID": "B7269EFE0B7A2AC3",
            "Status": "Resolved",
            "Verdict": "",
            "Assignee": "",
        },
    )
    def test_update_alert_invalid_uuid_error(
        self,
        script_session: SentinelOneSession,
        action_output: MockActionOutput,
    ) -> None:
        """Test handling of GraphQL error when alert ID is not a valid UUID."""
        alert_id = "B7269EFE0B7A2AC3"

        update_alert.main()

        assert action_output.results is not None
        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert action_output.results.result_value is False
        assert (
            f"Error executing action \"Update Alert\". Reason: alert with ID {alert_id} wasn't found in SentinelOne Singularity Operations Center. Please check the spelling."
            in action_output.results.output_message
        )
