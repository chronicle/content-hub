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

import contextlib
import dataclasses
import datetime
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
    from collections.abc import Callable, Container, Iterable, Mapping

    from soar_sdk.SiemplifyAction import SiemplifyAction
    from soar_sdk.SiemplifyDataModel import DomainEntityInfo

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
ASYNC_ACTION_TIMEOUT_THRESHOLD_MS: int = 35000
SUMMARY_NONE: str = "NONE"
TIMEOUT_MARKER_LOGGED_KEY: str = "timeout_marker_logged"


@dataclasses.dataclass(slots=True)
class SummaryCounts:
    """Target counts of an action run, for the summary line.

    Attributes:
        targets: The number of targets in scope.
        succeeded: The number of targets that succeeded.
        error_types: One error type for each failed target.
        skipped: The number of unsupported entities skipped.
    """

    targets: int
    succeeded: int
    error_types: list[str] = dataclasses.field(default_factory=list)
    skipped: int = 0


@dataclasses.dataclass(slots=True)
class SummaryRunContext:
    """Run-level error data of an action run, for the summary line.

    Attributes:
        error: The exception that ended the run, if any.
        error_type: The error type to report instead of the dominant one.
        fallback_error_type: Reported if nothing succeeded and no failure has a reason. Default INVALID_INPUT.
    """

    error: Exception | None = None
    error_type: str | None = None
    fallback_error_type: str | None = None


@dataclasses.dataclass(slots=True)
class OperationSummaryScope:
    """Target scope and failure context for an operation_results action run.

    Attributes:
        operation_results: Per-target results keyed by target identifier.
        agent_id_param: Explicit Agent Id parameter, if provided.
        error: The exception that ended the run, if any.
    """

    operation_results: Mapping[str, Mapping[str, str | None]] = dataclasses.field(default_factory=dict)
    agent_id_param: str | None = None
    error: Exception | None = None


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


def parse_bulk_acquisition_id(bulk_id: str | int | None) -> int:
    """Validate and parse a bulk acquisition ID into an integer.

    Args:
        bulk_id: Raw bulk acquisition ID.

    Returns:
        Validated integer bulk acquisition ID.

    Raises:
        ValueError: If the ID is empty or cannot be parsed as a numeric integer.
    """
    if not bulk_id or not str(bulk_id).strip():
        raise ValueError("Bulk Acquisition ID must not be empty.")

    try:
        return int(str(bulk_id).strip())
    except ValueError as value_error:
        raise ValueError(f"Bulk Acquisition ID must be a number, got: {bulk_id}.") from value_error


def classify_exception(error: Exception) -> tuple[str, str, int | None]:
    """Classify an exception for failure tagging and the action summary line.

    Args:
        error: The exception that failed a target or the run.

    Returns:
        The error type, the exception class name, and the HTTP status code or None.
    """
    underlying = error.__cause__ or error.__context__
    if not hasattr(error, "error_type") and isinstance(underlying, Exception):
        error = underlying
    http_status = _get_http_status(error)

    return _get_error_type(error, http_status), type(error).__name__, http_status


def _get_http_status(error: Exception) -> int | None:
    """Get the HTTP status code of an exception or of the HTTP error that caused it.

    Args:
        error: The exception to read.

    Returns:
        The HTTP status code, or None if there is none.
    """
    response: requests.Response | None = getattr(error, "response", None)
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
        The dominant error type, or NONE if there are no error types. Unrecognized types
        rank as, and return as, UNKNOWN_ERROR.
    """
    precedence = {error_type.value: index for index, error_type in enumerate(ErrorType)}
    fallback_rank = precedence[ErrorType.UNKNOWN_ERROR]
    dominant = min(error_types, key=lambda error_type: precedence.get(error_type, fallback_rank), default=SUMMARY_NONE)

    return dominant if dominant == SUMMARY_NONE or dominant in precedence else ErrorType.UNKNOWN_ERROR


def build_action_result_summary(
    execution_state: int,
    counts: SummaryCounts,
    context: SummaryRunContext | None = None,
) -> str:
    """Build the ACTION_RESULT_SUMMARY log line.

    Unfinished targets count as failed with the run error type when an exception
    ended the run. Unsupported entities remain in skipped.

    Args:
        execution_state: The execution state that the run ends with.
        counts: The target counts of the run.
        context: The run-level error data, if any.

    Returns:
        The summary line, with enums and counts only.
    """
    context = context or SummaryRunContext()
    error_types = counts.error_types
    failed = len(error_types)
    unfinished = max(counts.targets - counts.succeeded - failed, 0)
    exc_type, http_status = SUMMARY_NONE, None
    if context.error is not None:
        run_error_type, exc_type, http_status = classify_exception(context.error)
        error_types = [*error_types, run_error_type]
        failed += unfinished
    if not counts.succeeded:
        outcome = "FAILURE"
    elif failed or context.error is not None:
        outcome = "PARTIAL_SUCCESS"
    else:
        outcome = "SUCCESS"
    reason = context.error_type or dominant_error_type(error_types)
    if not counts.succeeded and reason == SUMMARY_NONE:
        reason = context.fallback_error_type or ErrorType.INVALID_INPUT

    return (
        f"ACTION_RESULT_SUMMARY v=1 outcome={outcome} error_type={reason} "
        f"execution_state={EXECUTION_STATE_NAMES[execution_state]} targets={counts.targets} failed={failed} "
        f"skipped={counts.skipped} exc_type={exc_type} http_status={http_status or SUMMARY_NONE}"
    )


def log_action_result_summary(
    siemplify: SiemplifyAction,
    execution_state: int,
    get_counts: Callable[[], SummaryCounts],
    context: SummaryRunContext | None = None,
) -> None:
    """Log the summary line of a finished run. Skip in-progress polls. Never raise.

    Args:
        siemplify: The action object.
        execution_state: The execution state that the run ends with.
        get_counts: Return the target counts of the run.
        context: The run-level error data, if any.
    """
    if execution_state == EXECUTION_STATE_INPROGRESS:
        return
    try:
        siemplify.LOGGER.info(build_action_result_summary(execution_state, get_counts(), context))
    except Exception as err:
        with contextlib.suppress(Exception):
            siemplify.LOGGER.warn(f"Failed to log action result summary: {err}")


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
        get_counts: Return the target counts of the run.
    """
    try:
        deadline = siemplify.async_total_duration_deadline
        next_poll_time = unix_now() + siemplify.async_polling_interval_in_sec * 1000
        if state.get(TIMEOUT_MARKER_LOGGED_KEY) or not deadline:
            return
        if next_poll_time < deadline - ASYNC_ACTION_TIMEOUT_THRESHOLD_MS:
            return
        state[TIMEOUT_MARKER_LOGGED_KEY] = True
        context = SummaryRunContext(error_type=ErrorType.TIMEOUT)
        siemplify.LOGGER.info(build_action_result_summary(EXECUTION_STATE_INPROGRESS, get_counts(), context))
    except Exception as err:
        with contextlib.suppress(Exception):
            siemplify.LOGGER.warn(f"Failed to log timeout marker: {err}")


def count_skipped_entities(target_entities: Iterable[DomainEntityInfo], supported_types: Container[str]) -> int:
    """Count target entities whose type is not supported by the action.

    Args:
        target_entities: The target entities attached to the action.
        supported_types: Entity types supported by the action.

    Returns:
        The unsupported entity count.
    """
    return sum(getattr(entity, "entity_type", "") not in supported_types for entity in target_entities)


def get_target_scope_counts(
    target_entities: Iterable[DomainEntityInfo] | None,
    agent_id_param: str | None = None,
) -> tuple[bool, int, int]:
    """Compute Agent Id flag, supported target count, and skipped count for entity-lookup actions.

    Args:
        target_entities: Target entities attached to the action, or None.
        agent_id_param: Explicit Agent Id parameter, if provided.

    Returns:
        Tuple of (has_agent_id, supported_target_count, skipped_entity_count).
    """
    if isinstance(agent_id_param, str) and agent_id_param.strip():
        return True, 1, 0
    entities = tuple(target_entities or ())
    skipped = count_skipped_entities(entities, AGENT_LOOKUP_ENTITY_TYPES)

    return False, len(entities) - skipped, skipped


def get_operation_summary_counts(
    operation_results: Mapping[str, Mapping[str, str | None]],
    targets: int = 0,
    pending_error_type: str | None = None,
) -> SummaryCounts:
    """Count the targets of an action that writes operation_results, for the summary line.

    Args:
        operation_results: The result of each target that the action processed.
        targets: The number of targets in scope, if it can be more than the number of processed targets.
        pending_error_type: The error type of targets in scope that were not processed, if they count as failed.

    Returns:
        The target counts of the run.
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

    return SummaryCounts(targets, succeeded, error_types)


def log_operation_result_summary(
    siemplify: SiemplifyAction,
    execution_state: int,
    scope: OperationSummaryScope,
) -> None:
    """Log the summary line of an action that runs on an Agent Id or on each HOSTNAME and ADDRESS entity.

    Never raise.

    Args:
        siemplify: The action object.
        execution_state: The execution state that the run ends with.
        scope: The operation results, explicit Agent Id, and run-level error.
    """

    def get_counts() -> SummaryCounts:
        if isinstance(scope.agent_id_param, str) and scope.agent_id_param.strip():
            targets, skipped = 1, 0
        else:
            _, targets, skipped = get_target_scope_counts(siemplify.target_entities)
        pending_error_type = ErrorType.TIMEOUT if execution_state == EXECUTION_STATE_TIMEDOUT else None
        counts = get_operation_summary_counts(scope.operation_results, targets, pending_error_type)
        counts.skipped = skipped

        return counts

    context = SummaryRunContext(error=scope.error, fallback_error_type=ErrorType.INVALID_INPUT)
    log_action_result_summary(siemplify, execution_state, get_counts, context)


def get_agent_lookup_failure_counts(
    target_entities: Iterable[DomainEntityInfo],
    lookup_errors: Iterable[Exception],
    skipped: int = 0,
) -> SummaryCounts:
    """Count the target of an action that found no agent ID, for the summary line.

    If no target entity can be looked up, no target was in scope. Else the target failed with the
    dominant error type of the lookup errors, or with ENDPOINT_NOT_FOUND.

    Args:
        target_entities: The target entities of the action.
        lookup_errors: The errors of the agent ID lookups.
        skipped: The number of unsupported entities skipped.

    Returns:
        The target counts of the run.
    """
    if not any(getattr(entity, "entity_type", "") in AGENT_LOOKUP_ENTITY_TYPES for entity in target_entities):
        return SummaryCounts(targets=0, succeeded=0, skipped=skipped)
    error_types = [classify_exception(error)[0] for error in lookup_errors]
    error_type = dominant_error_type([*error_types, ErrorType.ENDPOINT_NOT_FOUND])

    return SummaryCounts(targets=1, succeeded=0, error_types=[error_type], skipped=skipped)
