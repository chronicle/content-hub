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

"""Tests for the failure reasons and the summary line of the Isolate Endpoint action."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any
from unittest.mock import MagicMock, patch

import pytest
from soar_sdk.ScriptResult import (
    EXECUTION_STATE_COMPLETED,
    EXECUTION_STATE_FAILED,
    EXECUTION_STATE_INPROGRESS,
)
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyUtils import unix_now

from ..actions import IsolateEndpoint
from ..core.UtilsManager import TIMEOUT_MARKER_LOGGED_KEY
from .common import get_summary_lines, make_entity, run_action
from .test_action_result_summary import make_http_error

if TYPE_CHECKING:
    from collections.abc import Callable

DESCRIPTION = "Contain the endpoint"


def make_manager_setup(
    endpoints: dict[str, str],
    task_statuses: dict[str, str],
    errors: dict[str, Exception] | None = None,
    method: str = "isolate_endpoint",
) -> Callable[[MagicMock], None]:
    """Build a manager setup that maps lookups to endpoints and task URLs to task statuses.

    Args:
        endpoints: Endpoint GUID for each IP address, hostname, or agent UUID that exists.
        task_statuses: Task status for each task URL. A test can change it between polls.
        errors: Exception that the containment call raises for each endpoint GUID.
        method: The name of the manager containment method.

    Returns:
        The manager setup function for run_action.
    """

    def search_endpoint(
        ip: str | None = None,
        hostname: str | None = None,
        agent_id: str | None = None,
    ) -> MagicMock | None:
        guid = endpoints.get(ip or hostname or agent_id)
        return MagicMock(guid=guid) if guid else None

    def contain(description: str, guid: str) -> str:
        if errors and guid in errors:
            raise errors[guid]
        return f"url-{guid}"

    def setup(manager: MagicMock) -> None:
        manager.search_endpoint.side_effect = search_endpoint
        getattr(manager, method).side_effect = contain
        manager.get_task.side_effect = lambda task_url: MagicMock(id=f"task-{task_url}", status=task_statuses[task_url])

    return setup


def get_end_args(mock_siemplify: MagicMock) -> tuple[str, Any, int]:
    """Get the output message, result value, and execution state that the action ended with.

    Args:
        mock_siemplify: The mocked action object.

    Returns:
        The arguments of siemplify.end.
    """
    mock_siemplify.end.assert_called_once()

    return mock_siemplify.end.call_args.args


def get_json_by_entity(mock_siemplify: MagicMock) -> dict[str, Any]:
    """Get the JSON result of the action, keyed by target.

    Args:
        mock_siemplify: The mocked action object.

    Returns:
        The EntityResult of each target.
    """
    mock_siemplify.result.add_result_json.assert_called_once()
    json_result = mock_siemplify.result.add_result_json.call_args.args[0]

    return {item["Entity"]: item["EntityResult"] for item in json_result}


class TestIsolateEndpoint:
    """Tests for the failure reasons and the summary line of the action."""

    module = IsolateEndpoint
    method = "isolate_endpoint"
    verb = "isolate"

    def run(
        self,
        setup_args: tuple[Any, ...],
        entities: list[Any],
        agent_uuids: str = "",
        state: str | None = None,
    ) -> MagicMock:
        """Run the action once.

        Args:
            setup_args: Endpoints, task statuses, and optional errors for make_manager_setup.
            entities: The target entities.
            agent_uuids: The value of the Agent UUID parameter.
            state: The async state of the previous run. If None, run as the first run.

        Returns:
            The mocked action object.
        """
        params = {"Description": DESCRIPTION, "Agent UUID": agent_uuids}
        if state is not None:
            params["additional_data"] = state

        return run_action(
            self.module,
            params,
            make_manager_setup(*setup_args, method=self.method),
            entities=entities,
            main_args=(state is None,),
        )

    def test_success_by_entity(self) -> None:
        """Isolate a hostname entity and skip an unsupported entity. Log one SUCCESS summary."""
        entities = [make_entity("host1", EntityTypes.HOSTNAME), make_entity("http://x", EntityTypes.URL)]
        mock_siemplify = self.run(({"host1": "g1"}, {"url-g1": "succeeded"}), entities)

        _, result_value, status = get_end_args(mock_siemplify)
        assert (result_value, status) == (True, EXECUTION_STATE_COMPLETED)
        assert get_json_by_entity(mock_siemplify) == {"host1": {"task_id": "task-url-g1", "status": "succeeded"}}
        [summary] = get_summary_lines(mock_siemplify)
        assert summary["outcome"] == "SUCCESS"
        assert summary["error_type"] == "NONE"
        assert (summary["targets"], summary["failed"], summary["skipped"]) == ("1", "0", "1")

    def test_success_by_agent_uuid(self) -> None:
        """Process the entity and the Agent UUID together. Both targets count in the summary."""
        mock_siemplify = self.run(
            ({"host1": "g1", "g2": "g2"}, {"url-g1": "succeeded", "url-g2": "succeeded"}),
            [make_entity("host1", EntityTypes.HOSTNAME)],
            agent_uuids="g2",
        )

        assert get_end_args(mock_siemplify)[1:] == (True, EXECUTION_STATE_COMPLETED)
        assert set(get_json_by_entity(mock_siemplify)) == {"host1", "g2"}
        [summary] = get_summary_lines(mock_siemplify)
        assert (summary["outcome"], summary["targets"], summary["failed"]) == ("SUCCESS", "2", "0")

    def test_endpoint_not_found(self) -> None:
        """Tag an unknown entity and an unknown Agent UUID with ENDPOINT_NOT_FOUND."""
        mock_siemplify = self.run(({}, {}), [make_entity("10.0.0.1", EntityTypes.ADDRESS)], agent_uuids="missing")

        output_message, result_value, status = get_end_args(mock_siemplify)
        assert output_message == f"None of the provided endpoints were {self.verb}d."
        assert (result_value, status) == (False, EXECUTION_STATE_COMPLETED)
        assert get_json_by_entity(mock_siemplify) == {
            "10.0.0.1": {"error_type": "ENDPOINT_NOT_FOUND"},
            "missing": {"error_type": "ENDPOINT_NOT_FOUND"},
        }
        [summary] = get_summary_lines(mock_siemplify)
        assert (summary["outcome"], summary["error_type"]) == ("FAILURE", "ENDPOINT_NOT_FOUND")
        assert (summary["targets"], summary["failed"]) == ("2", "2")

    @pytest.mark.parametrize("task_status", ["failed", "rejected"])
    def test_task_failed(self, task_status: str) -> None:
        """Tag a task that Trend Vision One failed or rejected with VENDOR_ERROR. Keep the legacy keys."""
        entities = [make_entity("host1", EntityTypes.HOSTNAME)]
        mock_siemplify = self.run(({"host1": "g1"}, {"url-g1": task_status}), entities)

        assert get_end_args(mock_siemplify)[1:] == (False, EXECUTION_STATE_COMPLETED)
        assert get_json_by_entity(mock_siemplify) == {
            "host1": {"task_id": "task-url-g1", "status": task_status, "error_type": "VENDOR_ERROR"},
        }
        [summary] = get_summary_lines(mock_siemplify)
        assert (summary["outcome"], summary["error_type"], summary["failed"]) == ("FAILURE", "VENDOR_ERROR", "1")

    def test_target_exceptions_are_classified(self) -> None:
        """Tag the entity and Agent UUID whose containment call raises with the classified error type."""
        errors = {"g1": make_http_error(500), "g2": make_http_error(429)}
        mock_siemplify = self.run(
            ({"host1": "g1", "g2": "g2"}, {}, errors),
            [make_entity("host1", EntityTypes.HOSTNAME)],
            agent_uuids="g2",
        )

        assert get_end_args(mock_siemplify)[1:] == (False, EXECUTION_STATE_COMPLETED)
        assert get_json_by_entity(mock_siemplify) == {
            "host1": {"error_type": "VENDOR_ERROR"},
            "g2": {"error_type": "RATE_LIMITED"},
        }
        [summary] = get_summary_lines(mock_siemplify)
        assert (summary["outcome"], summary["error_type"], summary["failed"]) == ("FAILURE", "RATE_LIMITED", "2")

    def test_staggered_completion_keeps_error_types(self) -> None:
        """Finish targets across two polls. Error types from earlier runs reach the final JSON and summary."""
        entities = [make_entity(name, EntityTypes.HOSTNAME) for name in ("host1", "host2", "host3")]
        statuses = {"url-g1": "running", "url-g2": "running"}
        setup_args = ({"host1": "g1", "host2": "g2"}, statuses)

        first = self.run(setup_args, entities)
        _, state, status = get_end_args(first)
        assert status == EXECUTION_STATE_INPROGRESS
        assert json.loads(state)["json_results"]["host3"] == {"error_type": "ENDPOINT_NOT_FOUND"}
        statuses["url-g1"] = "succeeded"
        second = self.run(setup_args, entities, state=state)
        _, state, status = get_end_args(second)
        assert status == EXECUTION_STATE_INPROGRESS
        statuses["url-g2"] = "failed"
        third = self.run(setup_args, entities, state=state)

        assert get_summary_lines(first) == get_summary_lines(second) == []
        assert get_end_args(third)[1:] == (False, EXECUTION_STATE_COMPLETED)
        json_by_entity = get_json_by_entity(third)
        assert json_by_entity["host1"] == {"task_id": "task-url-g1", "status": "succeeded"}
        assert json_by_entity["host2"]["error_type"] == "VENDOR_ERROR"
        assert json_by_entity["host3"] == {"error_type": "ENDPOINT_NOT_FOUND"}
        [summary] = get_summary_lines(third)
        assert (summary["outcome"], summary["error_type"]) == ("PARTIAL_SUCCESS", "VENDOR_ERROR")
        assert (summary["targets"], summary["failed"]) == ("3", "2")

    def test_exception_ends_run(self) -> None:
        """Log the error type and HTTP status of an exception that ends a poll. Count unfinished targets as failed."""
        setup_args = ({"host1": "g1", "host2": "g2"}, {"url-g1": "running", "url-g2": "running"})
        entities = [make_entity("host1", EntityTypes.HOSTNAME), make_entity("host2", EntityTypes.HOSTNAME)]
        _, state, _ = get_end_args(self.run(setup_args, entities))

        def setup(manager: MagicMock) -> None:
            manager.get_task.side_effect = make_http_error(403)

        mock_siemplify = run_action(
            self.module,
            {"Description": DESCRIPTION, "additional_data": state},
            setup,
            entities=entities,
            main_args=(False,),
        )

        assert get_end_args(mock_siemplify)[1:] == (False, EXECUTION_STATE_FAILED)
        [summary] = get_summary_lines(mock_siemplify)
        assert (summary["outcome"], summary["error_type"]) == ("FAILURE", "PERMISSION_DENIED")
        assert (summary["execution_state"], summary["targets"], summary["failed"]) == ("FAILED", "2", "2")
        assert (summary["exc_type"], summary["http_status"]) == ("TrendVisionOneException", "403")

    def test_action_timeout_tags_pending_targets(self) -> None:
        """Tag pending targets with TIMEOUT when the action runs out of time, and log one FAILED summary."""
        entities = [make_entity("host1", EntityTypes.HOSTNAME), make_entity("host2", EntityTypes.HOSTNAME)]
        setup_args = ({"host1": "g1", "host2": "g2"}, {"url-g1": "running", "url-g2": "running"})
        with patch.object(self.module, "is_approaching_timeout", return_value=True):
            mock_siemplify = self.run(setup_args, entities)

        output_message, result_value, status = get_end_args(mock_siemplify)
        assert "Pending endpoints: host1, host2." in output_message
        assert (result_value, status) == (False, EXECUTION_STATE_FAILED)
        assert {result["error_type"] for result in get_json_by_entity(mock_siemplify).values()} == {"TIMEOUT"}
        [summary] = get_summary_lines(mock_siemplify)
        assert (summary["outcome"], summary["error_type"], summary["failed"]) == ("FAILURE", "TIMEOUT", "2")
        assert summary["exc_type"] == "TrendVisionOneTimeoutException"

    def test_timeout_marker_logged_once(self) -> None:
        """Log one IN_PROGRESS TIMEOUT marker near the async deadline and save the flag in the state."""
        entities = [make_entity("host1", EntityTypes.HOSTNAME)]
        manager_setup = make_manager_setup({"host1": "g1"}, {"url-g1": "running"}, method=self.method)

        def setup(manager: MagicMock) -> None:
            manager_setup(manager)
            manager.siemplify.async_total_duration_deadline = unix_now() + 1000
            manager.siemplify.async_polling_interval_in_sec = 60

        params = {"Description": DESCRIPTION}
        first = run_action(self.module, params, setup, entities=entities, main_args=(True,))
        _, state, status = get_end_args(first)
        params["additional_data"] = state
        second = run_action(self.module, params, setup, entities=entities, main_args=(False,))

        assert status == EXECUTION_STATE_INPROGRESS
        assert json.loads(state)[TIMEOUT_MARKER_LOGGED_KEY] is True
        [marker] = get_summary_lines(first)
        assert (marker["execution_state"], marker["error_type"], marker["failed"]) == ("IN_PROGRESS", "TIMEOUT", "1")
        assert get_summary_lines(second) == []
