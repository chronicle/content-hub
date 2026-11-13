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

"""Unit tests for the failure reason and action summary helpers of Trend Vision One."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
import requests
import urllib3
from soar_sdk.ScriptResult import (
    EXECUTION_STATE_COMPLETED,
    EXECUTION_STATE_FAILED,
    EXECUTION_STATE_INPROGRESS,
)
from soar_sdk.SiemplifyUtils import unix_now

from ..core import UtilsManager as utils
from ..core.api_utils import validate_response
from ..core.TrendVisionOneExceptions import TrendVisionOneException, TrendVisionOneTimeoutException
from ..core.TrendVisionOneManager import TrendVisionOneManager
from .common import SUMMARY_PATTERN, make_entity


def make_response(status_code: int, body: bytes = b"{}") -> requests.Response:
    """Build an HTTP response."""
    response = requests.Response()
    response.status_code = status_code
    response._content = body

    return response


def make_http_error(status_code: int) -> TrendVisionOneException:
    """Build the error that validate_response raises for an HTTP status code."""
    try:
        validate_response(make_response(status_code, b'{"error": {"message": "failed"}}'))
    except TrendVisionOneException as error:
        return error
    raise AssertionError("validate_response did not raise")


def real_adapter_error(kind: str) -> Exception:
    """Get the exception that requests raises when urllib3 fails (no network)."""
    pool = urllib3.connectionpool.HTTPSConnectionPool("api.xdr.trendmicro.com", 443)
    if kind == "connection":
        reason = urllib3.exceptions.NewConnectionError(pool, "Connection refused")
        urllib3_error = urllib3.exceptions.MaxRetryError(pool, "/v3.0/response/tasks/1", reason)
    elif kind == "read_timeout":
        urllib3_error = urllib3.exceptions.ReadTimeoutError(pool, "/v3.0/response/tasks/1", "Read timed out.")
    else:
        urllib3_error = urllib3.exceptions.ProtocolError("Connection aborted.", ConnectionResetError(104, "reset"))
    manager = TrendVisionOneManager("https://api.xdr.trendmicro.com", "token", verify_ssl=True, siemplify=MagicMock())
    with patch.object(urllib3.connectionpool.HTTPConnectionPool, "urlopen", side_effect=urllib3_error):
        try:
            manager.get_task("https://api.xdr.trendmicro.com/v3.0/response/tasks/1")
        except requests.RequestException as error:
            return error
    raise AssertionError("no error")


class TestClassifyException:
    """Tests for the mapping of failure signals to error types."""

    @pytest.mark.parametrize(
        ("error", "expected"),
        [
            (TrendVisionOneException("x", error_type="ENDPOINT_NOT_FOUND"), "ENDPOINT_NOT_FOUND"),
            (make_http_error(401), "AUTHENTICATION_FAILED"),
            (make_http_error(403), "PERMISSION_DENIED"),
            (make_http_error(429), "RATE_LIMITED"),
            (make_http_error(500), "VENDOR_ERROR"),
            (make_http_error(400), "VENDOR_ERROR"),
            (TrendVisionOneException("x"), "VENDOR_ERROR"),
            (TrendVisionOneTimeoutException("x"), "TIMEOUT"),
            (requests.ConnectionError("refused"), "CONNECTION_ERROR"),
            (requests.Timeout("timed out"), "CONNECTION_ERROR"),
            (ValueError("unexpected"), "UNKNOWN_ERROR"),
        ],
    )
    def test_error_type_by_exception(self, error: Exception, expected: str) -> None:
        """Verifies that each exception maps to its error type."""
        error_type, exc_type, _ = utils.classify_exception(error)

        assert error_type == expected
        assert exc_type == type(error).__name__

    def test_http_status_from_cause(self) -> None:
        """Verifies that the HTTP status comes from the HTTPError that validate_response wraps."""
        assert utils.classify_exception(make_http_error(403)) == (
            "PERMISSION_DENIED",
            "TrendVisionOneException",
            403,
        )

    def test_wrapped_error_is_unwrapped(self) -> None:
        """Verifies that a generic wrapper is classified by its cause."""
        try:
            raise RuntimeError("wrapper") from requests.ConnectionError("refused")
        except RuntimeError as error:
            assert utils.classify_exception(error) == ("CONNECTION_ERROR", "ConnectionError", None)

    def test_implicitly_chained_error_is_unwrapped(self) -> None:
        """Verifies that an error raised inside an except block without "from" is classified by its context."""
        error = RuntimeError("wrapper")
        error.__context__ = requests.ConnectionError("refused")

        assert utils.classify_exception(error) == ("CONNECTION_ERROR", "ConnectionError", None)

    @pytest.mark.parametrize("kind", ["connection", "read_timeout", "reset"])
    def test_real_requests_error_classified_as_connection_error(self, kind: str) -> None:
        """Verifies that real adapter network errors are classified as CONNECTION_ERROR."""
        error = real_adapter_error(kind)
        error_type, _, _ = utils.classify_exception(error)

        assert error_type == "CONNECTION_ERROR"


class TestSummaryLine:
    """Tests for the precedence and the format of the summary line."""

    def test_dominant_error_type_uses_member_order(self) -> None:
        """Verifies that the error type with the highest precedence wins."""
        assert utils.dominant_error_type(["FILE_NOT_FOUND", "AUTHENTICATION_FAILED", "TIMEOUT"]) == (
            "AUTHENTICATION_FAILED"
        )
        assert utils.dominant_error_type([]) == "NONE"

    def test_dominant_error_type_ranks_unknown_value_last(self) -> None:
        """Verifies that a value outside ErrorType does not raise and loses to a known error type."""
        assert utils.dominant_error_type(["NOT_AN_ERROR_TYPE", "TIMEOUT"]) == "TIMEOUT"
        assert utils.dominant_error_type(["NOT_AN_ERROR_TYPE"]) == "NOT_AN_ERROR_TYPE"

    def test_partial_success_line(self) -> None:
        """Verifies the exact format of a line with one success and one failure."""
        line = utils.build_action_result_summary(EXECUTION_STATE_COMPLETED, 2, 1, ["ENDPOINT_NOT_FOUND"])

        assert line == (
            "ACTION_RESULT_SUMMARY v=1 outcome=PARTIAL_SUCCESS error_type=ENDPOINT_NOT_FOUND "
            "execution_state=COMPLETED targets=2 failed=1 skipped=0 exc_type=NONE http_status=NONE"
        )
        assert SUMMARY_PATTERN.match(line)

    def test_default_invalid_input_when_nothing_succeeded(self) -> None:
        """Verify default INVALID_INPUT when succeeded is 0 and no failure reason is present."""
        zero_target_line = utils.build_action_result_summary(EXECUTION_STATE_COMPLETED, 0, 0, [])
        skipped_line = utils.build_action_result_summary(EXECUTION_STATE_COMPLETED, 0, 0, [], skipped=1)

        assert SUMMARY_PATTERN.match(zero_target_line)
        assert "outcome=FAILURE error_type=INVALID_INPUT" in zero_target_line
        assert SUMMARY_PATTERN.match(skipped_line)
        assert "outcome=FAILURE error_type=INVALID_INPUT" in skipped_line
        assert "targets=0 failed=0 skipped=1" in skipped_line

    def test_default_ignored_when_succeeded(self) -> None:
        """Verify the INVALID_INPUT default is not used when at least one target succeeded."""
        success_line = utils.build_action_result_summary(EXECUTION_STATE_COMPLETED, 1, 1, [])
        partial_line = utils.build_action_result_summary(EXECUTION_STATE_COMPLETED, 2, 1, ["ENDPOINT_NOT_FOUND"])

        assert SUMMARY_PATTERN.match(success_line)
        assert "outcome=SUCCESS error_type=NONE" in success_line
        assert SUMMARY_PATTERN.match(partial_line)
        assert "outcome=PARTIAL_SUCCESS error_type=ENDPOINT_NOT_FOUND" in partial_line

    def test_run_error_line(self) -> None:
        """Verifies that the exception that ended the run decides the error type and HTTP status."""
        line = utils.build_action_result_summary(
            EXECUTION_STATE_FAILED,
            1,
            0,
            [],
            error=make_http_error(401),
        )

        assert line == (
            "ACTION_RESULT_SUMMARY v=1 outcome=FAILURE error_type=AUTHENTICATION_FAILED "
            "execution_state=FAILED targets=1 failed=1 skipped=0 exc_type=TrendVisionOneException http_status=401"
        )

    def test_run_error_counts_unfinished_without_resetting_skipped(self) -> None:
        """Verify unfinished targets become failed on run error while skipped entities remain skipped."""
        line = utils.build_action_result_summary(
            EXECUTION_STATE_FAILED,
            2,
            1,
            [],
            skipped=3,
            error=make_http_error(401),
        )

        assert line == (
            "ACTION_RESULT_SUMMARY v=1 outcome=PARTIAL_SUCCESS error_type=AUTHENTICATION_FAILED "
            "execution_state=FAILED targets=2 failed=1 skipped=3 exc_type=TrendVisionOneException http_status=401"
        )

    def test_log_skips_in_progress(self) -> None:
        """Verifies that no line is logged on an in-progress poll."""
        siemplify = MagicMock()

        utils.log_action_result_summary(siemplify, EXECUTION_STATE_INPROGRESS, lambda: (1, 0, [], 0))

        siemplify.LOGGER.info.assert_not_called()

    def test_log_never_raises(self) -> None:
        """Verifies that a failure while counting or logging does not raise."""
        siemplify = MagicMock()
        siemplify.LOGGER.info.side_effect = RuntimeError("logger down")

        utils.log_action_result_summary(siemplify, EXECUTION_STATE_COMPLETED, lambda: (1, 1, [], 0))
        utils.log_action_result_summary(siemplify, EXECUTION_STATE_COMPLETED, lambda: 1 / 0)


class TestTimeoutMarker:
    """Tests for the one-shot timeout marker."""

    @staticmethod
    def make_action(deadline: int) -> MagicMock:
        """Build an action object with an async deadline."""
        siemplify = MagicMock()
        siemplify.async_total_duration_deadline = deadline
        siemplify.async_polling_interval_in_sec = 30
        return siemplify

    def test_marker_logged_once_near_deadline(self) -> None:
        """Verifies that the marker is logged once and the flag is saved in the state."""
        siemplify = self.make_action(unix_now() + 10_000)
        state = {}

        utils.log_timeout_marker_once(siemplify, state, lambda: (1, 0, ["TIMEOUT"], 0))
        utils.log_timeout_marker_once(siemplify, state, lambda: (1, 0, ["TIMEOUT"], 0))

        siemplify.LOGGER.info.assert_called_once()
        line = siemplify.LOGGER.info.call_args[0][0]
        assert SUMMARY_PATTERN.match(line)
        assert "error_type=TIMEOUT execution_state=IN_PROGRESS" in line
        assert state[utils.TIMEOUT_MARKER_LOGGED_KEY] is True

    def test_no_marker_far_from_deadline(self) -> None:
        """Verifies that no marker is logged when the deadline is far away or unknown."""
        siemplify = self.make_action(unix_now() + 3_600_000)
        state = {}

        utils.log_timeout_marker_once(siemplify, state, lambda: (1, 0, ["TIMEOUT"], 0))
        siemplify.async_total_duration_deadline = 0
        utils.log_timeout_marker_once(siemplify, state, lambda: (1, 0, ["TIMEOUT"], 0))

        siemplify.LOGGER.info.assert_not_called()
        assert state == {}

    def test_marker_never_raises(self) -> None:
        """Verifies that a failure while building the marker does not raise."""
        siemplify = self.make_action(unix_now() + 10_000)

        utils.log_timeout_marker_once(siemplify, {}, lambda: 1 / 0)

        siemplify.LOGGER.info.assert_not_called()

    def test_marker_keeps_skipped_count(self) -> None:
        """Verify log_timeout_marker_once keeps the skipped count of the callback."""
        siemplify = self.make_action(unix_now() + 10_000)

        utils.log_timeout_marker_once(siemplify, {}, lambda: (1, 0, ["TIMEOUT"], 2))

        line = siemplify.LOGGER.info.call_args[0][0]
        assert SUMMARY_PATTERN.match(line)
        assert "targets=1 failed=1 skipped=2" in line


def test_count_skipped_entities() -> None:
    """Verifies that count_skipped_entities counts only unsupported entity types."""
    entities = [
        make_entity("h", "HOSTNAME"),
        make_entity("u", "USERUNIQNAME"),
        make_entity("f", "FILENAME"),
    ]

    assert utils.count_skipped_entities(entities, ("HOSTNAME", "ADDRESS")) == 2
    assert utils.count_skipped_entities([], ("HOSTNAME", "ADDRESS")) == 0
