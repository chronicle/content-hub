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

from collections.abc import Callable, Container, Iterable, Mapping
from enum import StrEnum
from functools import partial
from typing import TYPE_CHECKING, Any

import os

import requests
from soar_sdk.ScriptResult import (
    EXECUTION_STATE_COMPLETED,
    EXECUTION_STATE_FAILED,
    EXECUTION_STATE_INPROGRESS,
    EXECUTION_STATE_TIMEDOUT,
)
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyUtils import convert_dict_to_json_result_dict, unix_now

from .TrendVisionOneManager import TrendVisionOneManager
from .TrendVisionOneExceptions import TrendVisionOneException, TrendVisionOneTimeoutException

from .constants import (
    CANCELED_STATUS,
    ENDPOINT_NOT_FOUND_MESSAGE,
    FAILED_STATUS,
    GLOBAL_TIMEOUT_THRESHOLD_IN_MIN,
    REJECTED_STATUS,
)
from . import datamodels

if TYPE_CHECKING:
    from soar_sdk.SiemplifyAction import SiemplifyAction


class ErrorType(StrEnum):
    """Failure reason of a target. Members are in precedence order, highest first."""

    AUTHENTICATION_FAILED = "AUTHENTICATION_FAILED"
    PERMISSION_DENIED = "PERMISSION_DENIED"
    CONFIGURATION_ERROR = "CONFIGURATION_ERROR"
    UNKNOWN_ERROR = "UNKNOWN_ERROR"
    CONNECTION_ERROR = "CONNECTION_ERROR"
    RATE_LIMITED = "RATE_LIMITED"
    VENDOR_ERROR = "VENDOR_ERROR"
    TIMEOUT = "TIMEOUT"
    UNSUPPORTED_ENDPOINT = "UNSUPPORTED_ENDPOINT"
    ENDPOINT_UNAVAILABLE = "ENDPOINT_UNAVAILABLE"
    FILE_RESTRICTED = "FILE_RESTRICTED"
    INVALID_INPUT = "INVALID_INPUT"
    CANCELLED = "CANCELLED"
    ENDPOINT_NOT_FOUND = "ENDPOINT_NOT_FOUND"
    FILE_NOT_FOUND = "FILE_NOT_FOUND"
    ALREADY_IN_STATE = "ALREADY_IN_STATE"


HTTP_STATUS_ERROR_TYPES: Mapping[int, ErrorType] = {
    401: ErrorType.AUTHENTICATION_FAILED,
    403: ErrorType.PERMISSION_DENIED,
    429: ErrorType.RATE_LIMITED,
}
EXCEPTION_ERROR_TYPES: tuple[tuple[type[Exception], ErrorType], ...] = (
    (requests.ConnectionError, ErrorType.CONNECTION_ERROR),
    (requests.Timeout, ErrorType.CONNECTION_ERROR),
    (TrendVisionOneTimeoutException, ErrorType.TIMEOUT),
)
TASK_STATUS_ERROR_TYPES: Mapping[str, ErrorType] = {
    FAILED_STATUS: ErrorType.VENDOR_ERROR,
    REJECTED_STATUS: ErrorType.PERMISSION_DENIED,
    CANCELED_STATUS: ErrorType.CANCELLED,
}
EXECUTION_STATE_NAMES: Mapping[int, str] = {
    EXECUTION_STATE_COMPLETED: "COMPLETED",
    EXECUTION_STATE_INPROGRESS: "IN_PROGRESS",
    EXECUTION_STATE_FAILED: "FAILED",
    EXECUTION_STATE_TIMEDOUT: "TIMEDOUT",
}
ASYNC_ACTION_TIMEOUT_THRESHOLD_MS = 35000
SUMMARY_NONE = "NONE"
TIMEOUT_MARKER_LOGGED_KEY = "timeout_marker_logged"
SummaryCounts = tuple[int, int, list[str], int]


def get_entity_original_identifier(entity: Any) -> str:
    """
    Helper function for getting entity original identifier
    Args:
        entity: entity from which function will get original identifier

    Returns:
        original identifier
    """
    return entity.additional_properties.get("OriginalIdentifier", entity.identifier)


def check_submit_files_in_system(files: list) -> list:
    """Return not accessible or not found files in filesystem.

    Args:
        files (list): list of files.

    Returns:
        list: list of not found files.
    """
    not_found_files = [
        file
        for file in files
        if not (os.path.exists(file) and os.access(file, os.R_OK))
    ]

    return not_found_files


def is_async_action_global_timeout_approaching(siemplify, start_time):
    return (
        siemplify.execution_deadline_unix_time_ms - start_time
        < GLOBAL_TIMEOUT_THRESHOLD_IN_MIN * 60 * 1000
    )


def process_agents(
    manager: TrendVisionOneManager,
    agent_uids: list[str],
) -> datamodels.AgentResult:
    """Process a list of agent UUIDs, searching for each agent and categorizing them as
    successful or failed.

    Args:
        manager (TrendVisionOneManager): An instance of the TrendVisionOneManager for
        interacting with the API.
        agent_uids (list[str]): A list of agent UUIDs to process.

    Returns:
        AgentResult: An object containing two lists: `successful_agents`
        (list of Endpoint objects) and `failed_agents` (list of agent UUIDs
        that could not be processed), and `failures` (the error and error_type
        of each failed agent UUID).
    """
    agent_result: datamodels.AgentResult = datamodels.AgentResult([], [], {})
    for agent_id in agent_uids:
        try:
            if (agent := manager.search_endpoint(agent_id=agent_id)) is not None:
                agent_result.successful_agents.append(agent)
            else:
                agent_result.failed_agents.append(agent_id)
                agent_result.failures[agent_id] = {
                    "error": ENDPOINT_NOT_FOUND_MESSAGE,
                    "error_type": ErrorType.ENDPOINT_NOT_FOUND,
                }
                manager.siemplify.LOGGER.info(f"Agent UUID not found: {agent_id}")

        except TrendVisionOneException as e:
            agent_result.failed_agents.append(agent_id)
            agent_result.failures[agent_id] = {"error": str(e), "error_type": classify_exception(e)[0]}
            manager.siemplify.LOGGER.error(f"An error occurred on agent: {agent_id}")
            manager.siemplify.LOGGER.exception(e)

    return agent_result


def classify_exception(error: Exception) -> tuple[str, str, int | None]:
    """Classify an exception for failure tagging and the action summary line.

    Args:
        error: The exception that failed a target or the run.

    Returns:
        The error type, the exception class name, and the HTTP status code or None.
    """
    if not hasattr(error, "error_type") and isinstance(error.__cause__, Exception):
        error = error.__cause__
    http_status = _get_http_status(error)

    return _get_error_type(error, http_status), type(error).__name__, http_status


def _get_http_status(error: Exception) -> int | None:
    """Get the HTTP status code of an exception or of the HTTP error that caused it.

    Args:
        error: The exception to read.

    Returns:
        The HTTP status code, or None if there is none.
    """
    response = getattr(error, "response", None)
    if response is None:
        response = getattr(error.__cause__ or error.__context__, "response", None)
    status_code = getattr(error, "status_code", None) or getattr(response, "status_code", None)

    return status_code if isinstance(status_code, int) else None


def _get_error_type(error: Exception, http_status: int | None) -> str:
    """Map an exception and its HTTP status code to an error type.

    Trend Vision One errors have an error_type attribute. The code that raises them sets it when it knows the
    failure reason.

    Args:
        error: The exception to map.
        http_status: The HTTP status code of the exception, or None.

    Returns:
        The error type.
    """
    if getattr(error, "error_type", None):
        return error.error_type
    for exception_type, error_type in EXCEPTION_ERROR_TYPES:
        if isinstance(error, exception_type):
            return error_type
    if http_status in HTTP_STATUS_ERROR_TYPES:
        return HTTP_STATUS_ERROR_TYPES[http_status]
    if hasattr(error, "error_type") or (http_status or 0) >= 500:
        return ErrorType.VENDOR_ERROR

    return ErrorType.UNKNOWN_ERROR


def dominant_error_type(error_types: Iterable[str]) -> str:
    """Pick the error type with the highest precedence.

    Args:
        error_types: The error types of the failed targets and of the run.

    Returns:
        The dominant error type, or NONE if there are no error types.
    """
    precedence = list(ErrorType)

    return min(error_types, key=precedence.index, default=SUMMARY_NONE)


def build_action_result_summary(
    execution_state: int,
    targets: int,
    succeeded: int,
    error_types: list[str],
    skipped: int = 0,
    error: Exception | None = None,
    error_type: str | None = None,
) -> str:
    """Build the ACTION_RESULT_SUMMARY log line.

    Unfinished targets count as failed with the run error type when an exception
    ended the run. Unsupported entities remain in skipped.

    Args:
        execution_state: The execution state that the run ends with.
        targets: The number of targets in scope.
        succeeded: The number of targets that succeeded.
        error_types: One error type for each failed target.
        skipped: The number of unsupported entities skipped.
        error: The exception that ended the run, if any.
        error_type: The error type to report instead of the dominant one. If nothing succeeded and no failure
            has a reason, INVALID_INPUT is reported.

    Returns:
        The summary line, with enums and counts only.
    """
    failed = len(error_types)
    unfinished = max(targets - succeeded - failed, 0)
    exc_type, http_status = SUMMARY_NONE, None
    if error is not None:
        run_error_type, exc_type, http_status = classify_exception(error)
        error_types = [*error_types, run_error_type]
        failed += unfinished
    if not succeeded:
        outcome = "FAILURE"
    elif failed or error is not None:
        outcome = "PARTIAL_SUCCESS"
    else:
        outcome = "SUCCESS"
    reason = error_type or dominant_error_type(error_types)
    if not succeeded and reason == SUMMARY_NONE:
        reason = ErrorType.INVALID_INPUT

    return (
        f"ACTION_RESULT_SUMMARY v=1 outcome={outcome} error_type={reason} "
        f"execution_state={EXECUTION_STATE_NAMES[execution_state]} targets={targets} failed={failed} "
        f"skipped={skipped} exc_type={exc_type} http_status={http_status or SUMMARY_NONE}"
    )


def log_action_result_summary(
    siemplify: SiemplifyAction,
    execution_state: int,
    get_counts: Callable[[], SummaryCounts],
    error: Exception | None = None,
) -> None:
    """Log the summary line of a finished run. Skip in-progress polls. Never raise.

    Args:
        siemplify: The action object.
        execution_state: The execution state that the run ends with.
        get_counts: Return (targets, succeeded, error_types, skipped).
        error: The exception that ended the run, if any.
    """
    if execution_state == EXECUTION_STATE_INPROGRESS:
        return
    try:
        siemplify.LOGGER.info(build_action_result_summary(execution_state, *get_counts(), error=error))
    except Exception:
        return


def log_timeout_marker_once(
    siemplify: SiemplifyAction,
    state: dict[str, Any],
    get_counts: Callable[[], SummaryCounts],
) -> None:
    """Log one IN_PROGRESS TIMEOUT summary line if the next poll can miss the async deadline.

    A flag in the async state makes sure that the line is logged once per action run. Never raise.

    Args:
        siemplify: The action object.
        state: The async state that the action saves for the next poll.
        get_counts: Return (targets, succeeded, error_types, skipped).
    """
    try:
        deadline = siemplify.async_total_duration_deadline
        next_poll_time = unix_now() + siemplify.async_polling_interval_in_sec * 1000
        if state.get(TIMEOUT_MARKER_LOGGED_KEY) or not deadline:
            return
        if next_poll_time < deadline - ASYNC_ACTION_TIMEOUT_THRESHOLD_MS:
            return
        state[TIMEOUT_MARKER_LOGGED_KEY] = True
        siemplify.LOGGER.info(
            build_action_result_summary(EXECUTION_STATE_INPROGRESS, *get_counts(), error_type=ErrorType.TIMEOUT)
        )
    except Exception:
        return


def count_skipped_entities(target_entities: Iterable[Any], supported_types: Container[str]) -> int:
    """Count target entities whose type is not supported by the action.

    Args:
        target_entities: The target entities attached to the action.
        supported_types: Entity types supported by the action.

    Returns:
        The unsupported entity count.
    """
    return sum(getattr(entity, "entity_type", "") not in supported_types for entity in target_entities)


def get_summary_counts(
    result_data: dict[str, Any],
    targets: int,
    skipped: int,
    pending_error_type: str | None = None,
) -> tuple[int, int, list[str], int]:
    """Count the targets of an Isolate or Unisolate Endpoint run for the action summary line.

    Args:
        result_data: The async state of the run.
        targets: The number of distinct targets in scope.
        skipped: The number of unsupported entities.
        pending_error_type: If set, count each pending target as failed with this error type.

    Returns:
        The targets, the succeeded count, one error type for each failed target, and the skipped count.
    """
    json_results = result_data.get("json_results", {})
    error_types = [result["error_type"] for result in json_results.values() if result.get("error_type")]
    if pending_error_type:
        pending = sum(1 for url in result_data.get("result_urls", {}).values() if url)
        error_types += [pending_error_type] * pending

    return targets, len(set(result_data.get("completed", []))), error_types, skipped


def log_run_summary(
    siemplify: SiemplifyAction,
    status: int,
    result_data: dict[str, Any],
    targets: int,
    supported_entity_types: Container[str],
    *,
    error: Exception | None = None,
) -> None:
    """Log the timeout marker on IN_PROGRESS polls and the summary line when an Isolate or Unisolate run ends.

    Args:
        siemplify: The action object.
        status: The execution state that the run ends with.
        result_data: The async state of the run. The timeout marker flag is saved in it.
        targets: The number of distinct targets in scope.
        supported_entity_types: Entity types supported by the action.
        error: The exception that ended the run, if any.
    """
    skipped = count_skipped_entities(siemplify.target_entities, supported_entity_types)
    get_counts = partial(get_summary_counts, result_data, targets, skipped)
    if status == EXECUTION_STATE_INPROGRESS:
        log_timeout_marker_once(siemplify, result_data, partial(get_counts, pending_error_type=ErrorType.TIMEOUT))
    log_action_result_summary(siemplify, status, get_counts, error=error)


def add_unfinished_json_result(siemplify: SiemplifyAction, result_data: dict[str, Any], error: Exception) -> None:
    """Attach the JSON result of an Isolate or Unisolate run that an exception ended.

    Finished targets keep their result. Each pending target gets the error text and error type of the exception.

    Args:
        siemplify: The action object.
        result_data: The async state of the run.
        error: The exception that ended the run.
    """
    json_results = result_data.get("json_results", {})
    failure = {"error": str(error).strip(), "error_type": classify_exception(error)[0]}
    for target in [key for key, url in result_data.get("result_urls", {}).items() if url]:
        json_results.setdefault(target, {}).update(failure)
    if json_results:
        siemplify.result.add_result_json(convert_dict_to_json_result_dict(json_results))


def get_task_failure(task: datamodels.Task) -> dict[str, str]:
    """Get the error text and error type of a response task that ended without success.

    Args:
        task: The task. Its status is failed, rejected, canceled, or another status that is not a success.

    Returns:
        The error and error_type keys of the JSON result.
    """
    message = (task.raw_data.get("error") or {}).get("message") or f"The task ended with status {task.status}."

    return {"error": message, "error_type": TASK_STATUS_ERROR_TYPES.get(task.status, ErrorType.VENDOR_ERROR)}


def get_endpoint_search_args(target: Any) -> dict[str, str]:
    """Build the TrendVisionOneManager.search_endpoint arguments for an entity or an Agent UUID.

    Args:
        target: A Hostname or IP Address entity, or an Agent UUID.

    Returns:
        The keyword arguments of TrendVisionOneManager.search_endpoint.
    """
    if isinstance(target, str):
        return {"agent_id": target}
    identifier = get_entity_original_identifier(target)
    if target.entity_type == EntityTypes.ADDRESS:
        return {"ip": identifier}

    return {"hostname": identifier}
