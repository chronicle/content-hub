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

import datetime
from collections.abc import Callable, Container, Iterable, Mapping
from enum import StrEnum
from typing import TYPE_CHECKING, Any

import requests
from soar_sdk.ScriptResult import (
    EXECUTION_STATE_COMPLETED,
    EXECUTION_STATE_FAILED,
    EXECUTION_STATE_INPROGRESS,
    EXECUTION_STATE_TIMEDOUT,
)
from soar_sdk.SiemplifyUtils import unix_now

if TYPE_CHECKING:
    from soar_sdk.SiemplifyAction import SiemplifyAction

UNIX_FORMAT = 1
DATETIME_FORMAT = 2
STORED_IDS_LIMIT = 3000


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
)
EXECUTION_STATE_NAMES: Mapping[int, str] = {
    EXECUTION_STATE_COMPLETED: "COMPLETED",
    EXECUTION_STATE_INPROGRESS: "IN_PROGRESS",
    EXECUTION_STATE_FAILED: "FAILED",
    EXECUTION_STATE_TIMEDOUT: "TIMEDOUT",
}
AGENT_LOOKUP_ENTITY_TYPES: tuple[str, ...] = ("HOSTNAME", "ADDRESS")
ASYNC_ACTION_TIMEOUT_THRESHOLD_MS = 35000
SUMMARY_NONE = "NONE"
TIMEOUT_MARKER_LOGGED_KEY = "timeout_marker_logged"
SummaryCounts = tuple[int, int, list[str]] | tuple[int, int, list[str], int]


def validate_response(response, error_msg="An error occurred"):
    """
    Validate response
    :param response: {requests.Response} The response to validate
    :param error_msg: {unicode} Default message to display on error
    """
    try:
        response.raise_for_status()

    except requests.HTTPError as error:
        raise Exception(f"{error_msg}: {error} {error.response.content}")

    return True


def get_earliest_event_at_datetime(alerts):
    """
    Get event_at datetime from earliest alert in alert list
    :param alerts: The alerts list
    :return: {str} The earliest event_at
    """
    alerts.sort(
        key=lambda alert: datetime.datetime.strptime(
            alert.get("event_at"), "%Y-%m-%dT%H:%M:%S.%fZ"
        )
    )
    return alerts[0].get("event_at")


def convert_comma_separated_to_list(comma_separated):
    """
    Convert comma-separated string to list
    :param comma_separated: String with comma-separated values
    :return: List of values
    """
    return (
        [item.strip() for item in comma_separated.split(",")] if comma_separated else []
    )


def convert_list_to_comma_string(values_list):
    """
    Convert list to comma-separated string
    :param values_list: List of values
    :return: String with comma-separated values
    """
    return (
        ", ".join(str(v) for v in values_list)
        if values_list and isinstance(values_list, list)
        else values_list
    )


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

    FireEye HX manager errors have an error_type attribute. The manager sets it when it knows the failure reason.

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
    fallback_error_type: str | None = None,
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
        error_type: The error type to report instead of the dominant one.
        fallback_error_type: Reported if nothing succeeded and no failure has a reason. Default INVALID_INPUT.

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
        reason = fallback_error_type or ErrorType.INVALID_INPUT

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
    fallback_error_type: str | None = None,
) -> None:
    """Log the summary line of a finished run. Skip in-progress polls. Never raise.

    Args:
        siemplify: The action object.
        execution_state: The execution state that the run ends with.
        get_counts: Return (targets, succeeded, error_types) or (targets, succeeded, error_types, skipped).
        error: The exception that ended the run, if any.
        fallback_error_type: Reported if nothing succeeded and no failure has a reason. Default INVALID_INPUT.
    """
    if execution_state == EXECUTION_STATE_INPROGRESS:
        return
    try:
        siemplify.LOGGER.info(
            build_action_result_summary(
                execution_state,
                *get_counts(),
                error=error,
                fallback_error_type=fallback_error_type,
            )
        )
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
        get_counts: Return (targets, succeeded, error_types) or (targets, succeeded, error_types, skipped).
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


def count_skipped_entities(
    target_entities: Iterable[Any],
    supported_types: Container[str],
    has_agent_id: bool = False,
) -> int:
    """Count target entities whose type is not supported by the action.

    Args:
        target_entities: The target entities attached to the action.
        supported_types: Entity types supported by the action.
        has_agent_id: Whether an explicit Agent Id overrides target entities.

    Returns:
        Zero when Agent Id overrides target entities, otherwise the unsupported entity count.
    """
    if has_agent_id:
        return 0

    return sum(getattr(entity, "entity_type", "") not in supported_types for entity in target_entities)


def get_operation_summary_counts(
    operation_results: Mapping[str, dict[str, Any]],
    targets: int = 0,
    pending_error_type: str | None = None,
) -> tuple[int, int, list[str]]:
    """Count the targets of an action that writes operation_results, for the summary line.

    Args:
        operation_results: The result of each target that the action processed.
        targets: The number of targets in scope, if it can be more than the number of processed targets.
        pending_error_type: The error type of targets in scope that were not processed, if they count as failed.

    Returns:
        The target count, the success count, and one error type per failed target.
    """
    error_types = [
        result.get("error_type") or ErrorType.UNKNOWN_ERROR
        for result in operation_results.values()
        if result.get("result") != "success"
    ]
    succeeded = len(operation_results) - len(error_types)
    targets = max(targets, len(operation_results))
    if pending_error_type:
        error_types += [pending_error_type] * (targets - len(operation_results))

    return targets, succeeded, error_types


def get_agent_lookup_failure_counts(
    target_entities: Iterable[Any],
    lookup_errors: Iterable[Exception],
) -> tuple[int, int, list[str]]:
    """Count the target of an action that found no agent ID, for the summary line.

    If no target entity can be looked up, no target was in scope. Else the target failed with the
    dominant error type of the lookup errors, or with ENDPOINT_NOT_FOUND.

    Args:
        target_entities: The target entities of the action.
        lookup_errors: The errors of the agent ID lookups.

    Returns:
        The target count, the success count, and one error type per failed target.
    """
    if not any(getattr(entity, "entity_type", "") in AGENT_LOOKUP_ENTITY_TYPES for entity in target_entities):
        return 0, 0, []
    error_types = [classify_exception(error)[0] for error in lookup_errors]

    return 1, 0, [dominant_error_type([*error_types, ErrorType.ENDPOINT_NOT_FOUND])]
