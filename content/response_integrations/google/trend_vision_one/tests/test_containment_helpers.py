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

"""Tests for the agent lookup and run summary helpers that Isolate and Unisolate Endpoint use."""

from __future__ import annotations

from unittest.mock import MagicMock

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_INPROGRESS
from soar_sdk.SiemplifyUtils import unix_now

from ..core.UtilsManager import (
    TIMEOUT_MARKER_LOGGED_KEY,
    get_summary_counts,
    log_run_summary,
    process_agents,
)
from .common import get_summary_lines, make_entity
from .test_action_result_summary import make_http_error

SUPPORTED_TYPES = ("ADDRESS", "HOSTNAME")
RESULT_DATA = {
    "result_urls": {"host2": "url-2", "host3": None},
    "json_results": {
        "host1": {"task_id": "t1", "status": "succeeded"},
        "host3": {"task_id": "t3", "status": "failed", "error_type": "VENDOR_ERROR"},
        "host4": {"error_type": "ENDPOINT_NOT_FOUND"},
    },
    "completed": ["host1", "host1"],
}


def test_process_agents_keeps_failure_of_each_failed_agent() -> None:
    """Tag a missing agent with ENDPOINT_NOT_FOUND and a lookup error with its error text and classified type."""
    manager = MagicMock()
    endpoint = MagicMock(guid="found")
    lookups = {"found": endpoint, "missing": None, "broken": make_http_error(403)}

    def search_endpoint(agent_id: str) -> MagicMock | None:
        if isinstance(lookups[agent_id], Exception):
            raise lookups[agent_id]
        return lookups[agent_id]

    manager.search_endpoint.side_effect = search_endpoint

    result = process_agents(manager, ["found", "missing", "broken"])

    assert result.successful_agents == [endpoint]
    assert result.failed_agents == ["missing", "broken"]
    assert result.failures == {
        "missing": {"error": "Endpoint was not found in Trend Vision One.", "error_type": "ENDPOINT_NOT_FOUND"},
        "broken": {"error": "failed", "error_type": "PERMISSION_DENIED"},
    }


def test_get_summary_counts() -> None:
    """Count distinct successes and tagged failures. Count pending targets only when an error type is given."""
    assert get_summary_counts(RESULT_DATA, 4, 1) == (4, 1, ["VENDOR_ERROR", "ENDPOINT_NOT_FOUND"], 1)
    expected_with_pending = ["VENDOR_ERROR", "ENDPOINT_NOT_FOUND", "TIMEOUT"]
    assert get_summary_counts(RESULT_DATA, 4, 1, "TIMEOUT")[2] == expected_with_pending
    assert get_summary_counts({}, 0, 0) == (0, 0, [], 0)


def test_log_run_summary_when_run_ends() -> None:
    """Log one summary line with skipped entities counted from the supported entity types."""
    siemplify = MagicMock()
    siemplify.target_entities = [make_entity("host1", "HOSTNAME"), make_entity("http://x", "DestinationURL")]

    log_run_summary(siemplify, EXECUTION_STATE_COMPLETED, RESULT_DATA, 4, SUPPORTED_TYPES)

    [summary] = get_summary_lines(siemplify)
    assert (summary["outcome"], summary["error_type"]) == ("PARTIAL_SUCCESS", "VENDOR_ERROR")
    assert (summary["targets"], summary["failed"], summary["skipped"]) == ("4", "2", "1")


def test_log_run_summary_in_progress_logs_only_timeout_marker() -> None:
    """Log no summary on an IN_PROGRESS poll. Near the deadline, log one marker that counts pending targets."""
    siemplify = MagicMock()
    siemplify.target_entities = []
    siemplify.async_total_duration_deadline = 0
    state = dict(RESULT_DATA)

    log_run_summary(siemplify, EXECUTION_STATE_INPROGRESS, state, 4, SUPPORTED_TYPES)
    assert get_summary_lines(siemplify) == []
    siemplify.async_total_duration_deadline = unix_now() + 1000
    siemplify.async_polling_interval_in_sec = 60
    log_run_summary(siemplify, EXECUTION_STATE_INPROGRESS, state, 4, SUPPORTED_TYPES)

    [marker] = get_summary_lines(siemplify)
    assert (marker["execution_state"], marker["error_type"], marker["failed"]) == ("IN_PROGRESS", "TIMEOUT", "3")
    assert state[TIMEOUT_MARKER_LOGGED_KEY] is True
