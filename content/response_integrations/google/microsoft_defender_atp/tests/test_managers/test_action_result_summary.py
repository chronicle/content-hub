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

import pytest
import requests
from integration_testing.requests.response import MockResponse
from TIPCommon.base.action.data_models import ExecutionState
from TIPCommon.exceptions import ActionSetupError, ParameterExtractionError

from microsoft_defender_atp.core.constants import ErrorType
from microsoft_defender_atp.core.exceptions import DefenderException, DefenderNotFoundException
from microsoft_defender_atp.core.MicrosoftDefenderATPManager import (
    MicrosoftDefenderATPError,
    MicrosoftDefenderATPForbiddenError,
    MicrosoftDefenderATPManager,
    MicrosoftDefenderATPValidationError,
)
from microsoft_defender_atp.core.UtilsManager import (
    ActionResultSummaryInput,
    build_action_result_summary,
    classify_exception,
    classify_live_response_failure,
    dominant_error_type,
    log_action_result_summary,
)
from microsoft_defender_atp.tests.common import SUMMARY_LINE_PATTERN


def _wrapped(wrapper: type[Exception], inner: Exception) -> Exception:
    """Wrap an exception the same way TIPCommon wraps setup and parameter failures.

    Args:
        wrapper: TIPCommon wrapper exception class.
        inner: Exception raised inside the wrapped step.

    Returns:
        The wrapper exception with the inner exception as __cause__.
    """
    try:
        raise wrapper(inner) from inner
    except wrapper as error:
        return error


@pytest.mark.parametrize(
    ("error", "expected"),
    [
        (DefenderNotFoundException("Machine with ID x was not found."), ("ENDPOINT_NOT_FOUND", None)),
        (MicrosoftDefenderATPError("Failed", status_code=401), ("AUTHENTICATION_FAILED", 401)),
        (MicrosoftDefenderATPError("Failed", status_code=403), ("PERMISSION_DENIED", 403)),
        (MicrosoftDefenderATPError("Rate limited", status_code=429), ("RATE_LIMITED", 429)),
        (MicrosoftDefenderATPError("Failed", status_code=500), ("VENDOR_ERROR", 500)),
        (MicrosoftDefenderATPError("Failed", status_code=404), ("VENDOR_ERROR", 404)),
        (MicrosoftDefenderATPError("There is no task with id 1"), ("VENDOR_ERROR", None)),
        (
            MicrosoftDefenderATPError("Unable to generate access token for Microsoft Defender ATP. x", status_code=400),
            ("AUTHENTICATION_FAILED", 400),
        ),
        (
            MicrosoftDefenderATPError("Unable to generate access token for Microsoft Defender ATP. x", status_code=429),
            ("RATE_LIMITED", 429),
        ),
        (
            MicrosoftDefenderATPError("Unable to generate access token for Microsoft Defender ATP. x", status_code=503),
            ("VENDOR_ERROR", 503),
        ),
        (MicrosoftDefenderATPForbiddenError(), ("PERMISSION_DENIED", None)),
        (MicrosoftDefenderATPValidationError("Invalid isolation type"), ("INVALID_INPUT", None)),
        (DefenderException("Machine already has an active request."), ("VENDOR_ERROR", None)),
        (requests.ConnectionError("refused"), ("CONNECTION_ERROR", None)),
        (requests.Timeout("timed out"), ("CONNECTION_ERROR", None)),
        (RuntimeError("crash"), ("UNKNOWN_ERROR", None)),
    ],
)
def test_classify_exception(error: Exception, expected: tuple[str, int | None]) -> None:
    """Each exception class and HTTP status maps to one error type and keeps the HTTP status."""
    error_type, exc_type, http_status = classify_exception(error)

    assert (error_type, http_status) == expected
    assert exc_type == type(error).__name__


@pytest.mark.parametrize(
    ("error", "expected"),
    [
        (_wrapped(ActionSetupError, MicrosoftDefenderATPError("x", status_code=403)), "PERMISSION_DENIED"),
        (_wrapped(ActionSetupError, Exception("Missing configuration")), "CONFIGURATION_ERROR"),
        (_wrapped(ActionSetupError, DefenderNotFoundException("x")), "CONFIGURATION_ERROR"),
        (_wrapped(ParameterExtractionError, Exception("Missing mandatory parameter File Path")), "INVALID_INPUT"),
    ],
)
def test_classify_exception_unwraps_tipcommon_wrappers(error: Exception, expected: str) -> None:
    """TIPCommon wrappers are unwrapped, and the wrapper type wins for a plain or not-found inner error."""
    error_type, exc_type, _ = classify_exception(error)

    assert error_type == expected
    assert exc_type == type(error.__cause__).__name__


@pytest.mark.parametrize(
    ("status", "reason", "expected"),
    [
        ("Failed", "File C:\\a.txt could not be located", ErrorType.FILE_NOT_FOUND),
        ("TimeOut", "Live Response action status: TimeOut.", ErrorType.TIMEOUT),
        ("Cancelled", "Live Response action status: Cancelled.", ErrorType.CANCELLED),
        ("Failed", "Unexpected agent error", ErrorType.VENDOR_ERROR),
    ],
)
def test_classify_live_response_failure(status: str, reason: str, expected: ErrorType) -> None:
    """A finished Live Response action maps to FILE_NOT_FOUND, TIMEOUT, CANCELLED, or VENDOR_ERROR."""
    assert classify_live_response_failure(status, reason) == expected


def test_dominant_error_type_uses_enum_order() -> None:
    """The dominant error type is the one with the highest precedence, or None if there is none."""
    assert dominant_error_type(["FILE_NOT_FOUND", "UNKNOWN_ERROR", "TIMEOUT"]) == "UNKNOWN_ERROR"
    assert dominant_error_type([]) is None


def test_dominant_error_type_treats_unrecognized_value_as_unknown() -> None:
    """Unrecognized error-type strings rank as and return UNKNOWN_ERROR."""
    assert dominant_error_type(["NOT_AN_ENUM"]) == "UNKNOWN_ERROR"
    assert dominant_error_type(["FILE_NOT_FOUND", "NOT_AN_ENUM"]) == "UNKNOWN_ERROR"


@pytest.mark.parametrize(
    ("kwargs", "expected"),
    [
        (
            {"execution_state": ExecutionState.COMPLETED, "target_results": {"a": None}},
            "outcome=SUCCESS error_type=NONE execution_state=COMPLETED targets=1 failed=0 skipped=0",
        ),
        (
            {"execution_state": 0, "target_results": {"a": None, "b": "FILE_NOT_FOUND"}, "skipped": 1},
            "outcome=PARTIAL_SUCCESS error_type=FILE_NOT_FOUND execution_state=COMPLETED targets=2 failed=1 skipped=1",
        ),
        (
            {"execution_state": ExecutionState.TIMED_OUT, "target_results": {"a": "TIMEOUT"}},
            "outcome=FAILURE error_type=TIMEOUT execution_state=TIMEDOUT targets=1 failed=1 skipped=0",
        ),
        (
            {"execution_state": 0, "target_results": {}, "skipped": 2, "fallback_error_type": "INVALID_INPUT"},
            "outcome=FAILURE error_type=INVALID_INPUT execution_state=COMPLETED targets=0 failed=0 skipped=2",
        ),
        (
            {"execution_state": 0, "target_results": {}, "fallback_error_type": None},
            "outcome=FAILURE error_type=INVALID_INPUT execution_state=COMPLETED targets=0 failed=0 skipped=0",
        ),
        (
            {"execution_state": 0, "target_results": {"a": None}, "fallback_error_type": "INVALID_INPUT"},
            "outcome=SUCCESS error_type=NONE execution_state=COMPLETED targets=1 failed=0 skipped=0",
        ),
    ],
)
def test_build_action_result_summary(kwargs: dict[str, object], expected: str) -> None:
    """The summary line has the fixed field order and holds only enums and counts."""
    line = build_action_result_summary(ActionResultSummaryInput(**kwargs))

    assert SUMMARY_LINE_PATTERN.fullmatch(line)
    assert line == f"ACTION_RESULT_SUMMARY v=1 {expected} exc_type=NONE http_status=NONE"


def test_build_action_result_summary_with_run_error() -> None:
    """An exception that ends the run adds its error type, class name, HTTP status, and unfinished targets."""
    line = build_action_result_summary(
        ActionResultSummaryInput(
            execution_state=ExecutionState.FAILED,
            target_results={"a": None},
            unfinished=1,
            error=MicrosoftDefenderATPError("Forbidden", status_code=403),
        )
    )

    assert line == (
        "ACTION_RESULT_SUMMARY v=1 outcome=PARTIAL_SUCCESS error_type=PERMISSION_DENIED execution_state=FAILED "
        "targets=2 failed=1 skipped=0 exc_type=MicrosoftDefenderATPError http_status=403"
    )


def test_log_action_result_summary_logs_warn_on_failure() -> None:
    """If summary logging fails, the wrapper emits a warning with the error."""
    warnings: list[str] = []

    class _WarnOnlyLogger:
        def info(self, _: str) -> None:
            raise RuntimeError("logger error")

        def warn(self, message: str) -> None:
            warnings.append(message)

    log_action_result_summary(
        _WarnOnlyLogger(),
        lambda: ActionResultSummaryInput(execution_state=ExecutionState.COMPLETED, target_results={"a": None}),
    )

    assert warnings == ["Failed to log action result summary: logger error"]


def test_log_action_result_summary_never_raises() -> None:
    """If both info and warn raise, the wrapper still returns without raising."""

    class _BrokenLogger:
        def info(self, _: str) -> None:
            raise RuntimeError("logger error")

        def warn(self, _: str) -> None:
            raise RuntimeError("warn error")

    log_action_result_summary(
        _BrokenLogger(),
        lambda: ActionResultSummaryInput(execution_state=ExecutionState.COMPLETED, target_results={"a": None}),
    )


@pytest.mark.parametrize(
    ("response", "message"),
    [
        (MockResponse({"error": {"message": "Forbidden"}}, status_code=403), "Failed to fetch. Forbidden"),
        (MockResponse(["unexpected"], status_code=502), "Failed to fetch"),
        (MockResponse("not json", status_code=500), "Failed to fetch: "),
        (MockResponse({}, status_code=429), "Action ran into rate limiting. Please try again in a few minutes."),
    ],
)
def test_validate_response_keeps_status_code(response: MockResponse, message: str) -> None:
    """The raised error keeps the HTTP status code for JSON, non-JSON, and rate-limit responses."""
    with pytest.raises(MicrosoftDefenderATPError) as error:
        MicrosoftDefenderATPManager._validate_response(response, "Failed to fetch")

    assert error.value.status_code == response.status_code
    assert str(error.value).startswith(message)
