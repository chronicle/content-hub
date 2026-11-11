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

"""Unit tests for the failure reason and action summary helpers of FireEyeHX."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
import requests
from soar_sdk.ScriptResult import (
    EXECUTION_STATE_COMPLETED,
    EXECUTION_STATE_FAILED,
    EXECUTION_STATE_INPROGRESS,
)
from soar_sdk.SiemplifyUtils import unix_now

from ..core import UtilsManager as utils
from ..core.FireEyeHXManager import FireEyeHXManager, FireEyeHXManagerError, FireEyeHXNotFoundError
from .common import SUMMARY_PATTERN, make_entity


def make_response(status_code: int, body: bytes = b"{}") -> requests.Response:
    """Build an HTTP response.

    Args:
        status_code: The HTTP status code.
        body: The response body.

    Returns:
        The response.
    """
    response = requests.Response()
    response.status_code = status_code
    response._content = body
    return response


def make_manager() -> FireEyeHXManager:
    """Build a manager without a login request.

    Returns:
        The manager.
    """
    with patch.object(FireEyeHXManager, "get_token", return_value="token"):
        return FireEyeHXManager(api_root="https://hx.example.com", username="user", password="password")


class TestClassifyException:
    """Tests for the mapping of failure signals to error types."""

    @pytest.mark.parametrize(
        ("error", "expected"),
        [
            (FireEyeHXNotFoundError("x", status_code=404, error_type="ENDPOINT_NOT_FOUND"), "ENDPOINT_NOT_FOUND"),
            (FireEyeHXNotFoundError("x", status_code=404, error_type="ENDPOINT_UNAVAILABLE"), "ENDPOINT_UNAVAILABLE"),
            (FireEyeHXManagerError("x", status_code=405, error_type="UNSUPPORTED_ENDPOINT"), "UNSUPPORTED_ENDPOINT"),
            (FireEyeHXManagerError("x", status_code=401), "AUTHENTICATION_FAILED"),
            (FireEyeHXManagerError("x", status_code=403), "PERMISSION_DENIED"),
            (FireEyeHXManagerError("x", status_code=429), "RATE_LIMITED"),
            (FireEyeHXManagerError("x", status_code=500), "VENDOR_ERROR"),
            (FireEyeHXNotFoundError("x", status_code=404), "VENDOR_ERROR"),
            (
                FireEyeHXManagerError(
                    "Authentication failed. No X-FeApi-Token found.",
                    error_type="AUTHENTICATION_FAILED",
                ),
                "AUTHENTICATION_FAILED",
            ),
            (FireEyeHXManagerError("x"), "VENDOR_ERROR"),
            (requests.ConnectionError("refused"), "CONNECTION_ERROR"),
            (requests.exceptions.SSLError("bad certificate"), "CONNECTION_ERROR"),
            (requests.Timeout("timed out"), "CONNECTION_ERROR"),
            (ValueError("unexpected"), "UNKNOWN_ERROR"),
        ],
    )
    def test_error_type_by_exception(self, error: Exception, expected: str) -> None:
        """Verifies that each exception maps to its error type."""
        error_type, exc_type, _ = utils.classify_exception(error)

        assert error_type == expected
        assert exc_type == type(error).__name__

    def test_http_status_from_status_code(self) -> None:
        """Verifies that the status_code of a manager error is the HTTP status."""
        assert utils.classify_exception(FireEyeHXManagerError("x", status_code=403)) == (
            "PERMISSION_DENIED",
            "FireEyeHXManagerError",
            403,
        )

    def test_http_error_5xx_without_vendor_class(self) -> None:
        """Verifies that a bare HTTPError with a 5xx status maps to VENDOR_ERROR."""
        error = requests.HTTPError(response=make_response(503))

        assert utils.classify_exception(error) == ("VENDOR_ERROR", "HTTPError", 503)

    def test_wrapped_error_is_unwrapped(self) -> None:
        """Verifies that a generic wrapper is classified by its cause."""
        try:
            raise RuntimeError("wrapper") from requests.ConnectionError("refused")
        except RuntimeError as error:
            assert utils.classify_exception(error) == ("CONNECTION_ERROR", "ConnectionError", None)


class TestSummaryLine:
    """Tests for the precedence and the format of the summary line."""

    def test_dominant_error_type_uses_member_order(self) -> None:
        """Verifies that the error type with the highest precedence wins."""
        assert utils.dominant_error_type(["FILE_NOT_FOUND", "AUTHENTICATION_FAILED", "TIMEOUT"]) == (
            "AUTHENTICATION_FAILED"
        )
        assert utils.dominant_error_type([]) == "NONE"

    def test_partial_success_line(self) -> None:
        """Verifies the exact format of a line with one success and one failure."""
        line = utils.build_action_result_summary(EXECUTION_STATE_COMPLETED, 2, 1, ["ENDPOINT_NOT_FOUND"])

        assert line == (
            "ACTION_RESULT_SUMMARY v=1 outcome=PARTIAL_SUCCESS error_type=ENDPOINT_NOT_FOUND "
            "execution_state=COMPLETED targets=2 failed=1 skipped=0 exc_type=NONE http_status=NONE"
        )
        assert SUMMARY_PATTERN.match(line)

    def test_zero_targets_line_uses_fallback(self) -> None:
        """Verifies that a run with no targets and no exception reports the fallback reason."""
        line = utils.build_action_result_summary(
            EXECUTION_STATE_COMPLETED,
            0,
            0,
            [],
            fallback_error_type="INVALID_INPUT",
        )

        assert "outcome=FAILURE error_type=INVALID_INPUT" in line
        assert "targets=0 failed=0 skipped=0" in line

    def test_default_invalid_input_when_nothing_succeeded(self) -> None:
        """Verify default INVALID_INPUT when succeeded is 0 and no failure reason is present."""
        zero_target_line = utils.build_action_result_summary(EXECUTION_STATE_COMPLETED, 0, 0, [])
        skipped_line = utils.build_action_result_summary(EXECUTION_STATE_COMPLETED, 0, 0, [], skipped=1)

        assert SUMMARY_PATTERN.match(zero_target_line)
        assert "outcome=FAILURE error_type=INVALID_INPUT" in zero_target_line
        assert SUMMARY_PATTERN.match(skipped_line)
        assert "outcome=FAILURE error_type=INVALID_INPUT" in skipped_line
        assert "targets=0 failed=0 skipped=1" in skipped_line

    def test_fallback_error_type_ignored_when_succeeded(self) -> None:
        """Verify fallback_error_type is ignored when at least one target succeeded."""
        success_line = utils.build_action_result_summary(
            EXECUTION_STATE_COMPLETED,
            1,
            1,
            [],
            fallback_error_type="INVALID_INPUT",
        )
        partial_line = utils.build_action_result_summary(
            EXECUTION_STATE_COMPLETED,
            2,
            1,
            ["ENDPOINT_NOT_FOUND"],
            fallback_error_type="INVALID_INPUT",
        )

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
            error=FireEyeHXManagerError("x", status_code=401),
        )

        assert line == (
            "ACTION_RESULT_SUMMARY v=1 outcome=FAILURE error_type=AUTHENTICATION_FAILED "
            "execution_state=FAILED targets=1 failed=1 skipped=0 exc_type=FireEyeHXManagerError http_status=401"
        )

    def test_run_error_counts_unfinished_without_resetting_skipped(self) -> None:
        """Verify unfinished targets become failed on run error while skipped entities remain skipped."""
        line = utils.build_action_result_summary(
            EXECUTION_STATE_FAILED,
            2,
            1,
            [],
            skipped=3,
            error=FireEyeHXManagerError("x", status_code=401),
        )

        assert line == (
            "ACTION_RESULT_SUMMARY v=1 outcome=PARTIAL_SUCCESS error_type=AUTHENTICATION_FAILED "
            "execution_state=FAILED targets=2 failed=1 skipped=3 exc_type=FireEyeHXManagerError http_status=401"
        )

    def test_log_accepts_three_and_four_tuple_counts(self) -> None:
        """Verify log_action_result_summary accepts both 3-tuple and 4-tuple count callbacks."""
        siemplify = MagicMock()

        utils.log_action_result_summary(siemplify, EXECUTION_STATE_COMPLETED, lambda: (1, 1, []))
        utils.log_action_result_summary(siemplify, EXECUTION_STATE_COMPLETED, lambda: (1, 1, [], 2))

        first_line = siemplify.LOGGER.info.call_args_list[0].args[0]
        second_line = siemplify.LOGGER.info.call_args_list[1].args[0]
        assert "targets=1 failed=0 skipped=0" in first_line
        assert "targets=1 failed=0 skipped=2" in second_line

    def test_log_skips_in_progress(self) -> None:
        """Verifies that no line is logged on an in-progress poll."""
        siemplify = MagicMock()

        utils.log_action_result_summary(siemplify, EXECUTION_STATE_INPROGRESS, lambda: (1, 0, []))

        siemplify.LOGGER.info.assert_not_called()

    def test_log_never_raises(self) -> None:
        """Verifies that a failure while counting or logging does not raise."""
        siemplify = MagicMock()
        siemplify.LOGGER.info.side_effect = RuntimeError("logger down")

        utils.log_action_result_summary(siemplify, EXECUTION_STATE_COMPLETED, lambda: (1, 1, []))
        utils.log_action_result_summary(siemplify, EXECUTION_STATE_COMPLETED, lambda: 1 / 0)


class TestTimeoutMarker:
    """Tests for the one-shot timeout marker."""

    @staticmethod
    def make_action(deadline: int) -> MagicMock:
        """Build an action object with an async deadline.

        Args:
            deadline: The async deadline in Unix milliseconds.

        Returns:
            The action object.
        """
        siemplify = MagicMock()
        siemplify.async_total_duration_deadline = deadline
        siemplify.async_polling_interval_in_sec = 30
        return siemplify

    def test_marker_logged_once_near_deadline(self) -> None:
        """Verifies that the marker is logged once and the flag is saved in the state."""
        siemplify = self.make_action(unix_now() + 10_000)
        state = {}

        utils.log_timeout_marker_once(siemplify, state, lambda: (1, 0, ["TIMEOUT"]))
        utils.log_timeout_marker_once(siemplify, state, lambda: (1, 0, ["TIMEOUT"]))

        siemplify.LOGGER.info.assert_called_once()
        line = siemplify.LOGGER.info.call_args[0][0]
        assert SUMMARY_PATTERN.match(line)
        assert "error_type=TIMEOUT execution_state=IN_PROGRESS" in line
        assert state[utils.TIMEOUT_MARKER_LOGGED_KEY] is True

    def test_no_marker_far_from_deadline(self) -> None:
        """Verifies that no marker is logged when the deadline is far away or unknown."""
        siemplify = self.make_action(unix_now() + 3_600_000)
        state = {}

        utils.log_timeout_marker_once(siemplify, state, lambda: (1, 0, ["TIMEOUT"]))
        siemplify.async_total_duration_deadline = 0
        utils.log_timeout_marker_once(siemplify, state, lambda: (1, 0, ["TIMEOUT"]))

        siemplify.LOGGER.info.assert_not_called()
        assert state == {}

    def test_marker_never_raises(self) -> None:
        """Verifies that a failure while building the marker does not raise."""
        siemplify = self.make_action(unix_now() + 10_000)

        utils.log_timeout_marker_once(siemplify, {}, lambda: 1 / 0)

        siemplify.LOGGER.info.assert_not_called()

    def test_marker_accepts_four_tuple_counts(self) -> None:
        """Verify log_timeout_marker_once preserves skipped count from a 4-tuple callback."""
        siemplify = self.make_action(unix_now() + 10_000)

        utils.log_timeout_marker_once(siemplify, {}, lambda: (1, 0, ["TIMEOUT"], 2))

        line = siemplify.LOGGER.info.call_args[0][0]
        assert SUMMARY_PATTERN.match(line)
        assert "targets=1 failed=1 skipped=2" in line


class TestSummaryCounts:
    """Tests for the target counts of the actions."""

    def test_operation_counts(self) -> None:
        """Verifies the counts of processed targets and of targets that were not processed."""
        operation_results = {
            "a": {"result": "success"},
            "b": {"result": "failure", "error_type": "ENDPOINT_NOT_FOUND"},
            "c": {"result": "failure"},
        }

        assert utils.get_operation_summary_counts(operation_results) == (
            3,
            1,
            ["ENDPOINT_NOT_FOUND", "UNKNOWN_ERROR"],
        )
        assert utils.get_operation_summary_counts(operation_results, 4, "TIMEOUT") == (
            4,
            1,
            ["ENDPOINT_NOT_FOUND", "UNKNOWN_ERROR", "TIMEOUT"],
        )

    def test_lookup_failure_without_entities(self) -> None:
        """Verifies that no target is in scope if no entity can be looked up."""
        assert utils.get_agent_lookup_failure_counts([make_entity("u", "USERUNIQNAME")], []) == (0, 0, [])

    def test_lookup_failure_not_found(self) -> None:
        """Verifies that an empty lookup reports ENDPOINT_NOT_FOUND."""
        assert utils.get_agent_lookup_failure_counts([make_entity("h", "HOSTNAME")], []) == (
            1,
            0,
            ["ENDPOINT_NOT_FOUND"],
        )

    def test_lookup_failure_keeps_lookup_error(self) -> None:
        """Verifies that a failed lookup request wins over ENDPOINT_NOT_FOUND."""
        errors = [requests.ConnectionError("refused")]

        assert utils.get_agent_lookup_failure_counts([make_entity("h", "HOSTNAME")], errors) == (
            1,
            0,
            ["CONNECTION_ERROR"],
        )

    def test_count_skipped_entities(self) -> None:
        """Verify count_skipped_entities counts unsupported entities unless Agent Id overrides."""
        entities = [
            make_entity("h", "HOSTNAME"),
            make_entity("u", "USERUNIQNAME"),
            make_entity("f", "FILENAME"),
        ]

        assert utils.count_skipped_entities(entities, utils.AGENT_LOOKUP_ENTITY_TYPES) == 2
        assert utils.count_skipped_entities(entities, utils.AGENT_LOOKUP_ENTITY_TYPES, has_agent_id=True) == 0
        assert utils.count_skipped_entities([], utils.AGENT_LOOKUP_ENTITY_TYPES) == 0


class TestManagerErrors:
    """Tests for the status code and failure reason of manager errors."""

    @pytest.mark.parametrize(
        ("status_code", "body", "error_class", "expected"),
        [
            (404, b"Host not found", FireEyeHXNotFoundError, "ENDPOINT_NOT_FOUND"),
            (404, b"Device not found", FireEyeHXNotFoundError, "ENDPOINT_UNAVAILABLE"),
            (404, b"Not here", FireEyeHXNotFoundError, None),
            (405, b"", FireEyeHXManagerError, "UNSUPPORTED_ENDPOINT"),
        ],
    )
    def test_create_file_acquisition_errors(
        self,
        status_code: int,
        body: bytes,
        error_class: type[Exception],
        expected: str | None,
    ) -> None:
        """Verifies that each create acquisition failure keeps its message and gets its reason."""
        manager = make_manager()
        manager.session.post = MagicMock(return_value=make_response(status_code, body))

        with pytest.raises(error_class) as raised:
            manager.create_file_acquisition("agent-1", "C:\\temp", "a.exe")

        assert str(raised.value).startswith(f"HTTP Error {status_code}")
        assert raised.value.status_code == status_code
        assert raised.value.error_type == expected

    def test_validate_response_not_found_reason(self) -> None:
        """Verifies that a host-scoped HTTP 404 reports ENDPOINT_NOT_FOUND."""
        manager = make_manager()
        manager.session.post = MagicMock(return_value=make_response(404, b'{"message": "Host not found"}'))

        with pytest.raises(FireEyeHXNotFoundError) as raised:
            manager.contain_host_by_id("agent-1")

        assert str(raised.value) == "Unable to contain host agent-1: Host not found"
        assert utils.classify_exception(raised.value) == ("ENDPOINT_NOT_FOUND", "FireEyeHXNotFoundError", 404)

    @pytest.mark.parametrize(
        ("body", "expected_attr", "expected_classified"),
        [
            (b'{"details": [{"message": "Host not found"}]}', "ENDPOINT_NOT_FOUND", "ENDPOINT_NOT_FOUND"),
            (b'{"details": [{"message": "Containment state not found"}]}', None, "VENDOR_ERROR"),
        ],
    )
    def test_validate_response_404_details(
        self,
        body: bytes,
        expected_attr: str | None,
        expected_classified: str,
    ) -> None:
        """Verify HTTP 404 details map Host not found to ENDPOINT_NOT_FOUND and other details to VENDOR_ERROR.

        Args:
            body: Raw JSON error response body.
            expected_attr: Expected error_type attribute on the raised FireEyeHXNotFoundError.
            expected_classified: Expected error_type returned by classify_exception.
        """
        manager = make_manager()
        manager.session.get = MagicMock(return_value=make_response(404, body))

        with pytest.raises(FireEyeHXNotFoundError) as raised:
            manager.get_containment_status("agent-1")

        assert raised.value.status_code == 404
        assert raised.value.error_type == expected_attr
        assert utils.classify_exception(raised.value) == (expected_classified, "FireEyeHXNotFoundError", 404)

    def test_validate_response_status_code(self) -> None:
        """Verifies that other HTTP errors keep their status code."""
        manager = make_manager()
        manager.session.delete = MagicMock(return_value=make_response(403, b'{"message": "Forbidden"}'))

        with pytest.raises(FireEyeHXManagerError) as raised:
            manager.cancel_containment_by_id("agent-1")

        assert utils.classify_exception(raised.value)[0] == "PERMISSION_DENIED"
        assert raised.value.status_code == 403

    def test_host_name_lookup_not_found(self) -> None:
        """Verifies that an empty host search raises a not-found error with its old message."""
        manager = make_manager()
        manager.get_hosts = MagicMock(return_value=[])

        with pytest.raises(FireEyeHXNotFoundError, match=r"^Host host-1 was not found\.$") as raised:
            manager.get_host_by_name("host-1")

        assert raised.value.error_type == "ENDPOINT_NOT_FOUND"

    def test_host_name_lookup_keeps_request_error(self) -> None:
        """Verifies that a failed host search is not reported as not found."""
        manager = make_manager()
        manager.get_hosts = MagicMock(side_effect=requests.ConnectionError("refused"))

        with pytest.raises(requests.ConnectionError):
            manager.get_host_by_name("host-1")

    def test_resolve_continues_after_failed_lookup(self) -> None:
        """Verifies that one failed host-name lookup does not stop the lookup of the next entities."""
        manager = make_manager()
        host = MagicMock(_id="agent-2")
        manager.get_hosts = MagicMock(side_effect=[requests.ConnectionError("refused"), [host]])
        entities = [make_entity("host-1", "HOSTNAME"), make_entity("host-2", "HOSTNAME")]

        assert manager.resolve_agent_id_from_entities(entities) == "agent-2"
        assert [type(error) for error in manager.lookup_errors] == [requests.ConnectionError]

    def test_resolve_address_records_not_found_lookup_error(self) -> None:
        """Verify ADDRESS resolution records FireEyeHXNotFoundError in lookup_errors and continues."""
        not_found_error = FireEyeHXNotFoundError("Unable to get hosts: Route not found", status_code=404)
        host = MagicMock(_id="agent-2", primary_ip_address="10.0.0.2", last_poll_timestamp=1)

        manager = make_manager()
        manager.get_hosts = MagicMock(side_effect=[not_found_error, [host]])
        entities = [make_entity("10.0.0.1", "ADDRESS"), make_entity("10.0.0.2", "ADDRESS")]

        assert manager.resolve_agent_id_from_entities(entities) == "agent-2"
        assert manager.lookup_errors == [not_found_error]

        failing_manager = make_manager()
        failing_manager.get_hosts = MagicMock(side_effect=not_found_error)
        single_entity = [make_entity("10.0.0.1", "ADDRESS")]

        assert failing_manager.resolve_agent_id_from_entities(single_entity) is None
        assert failing_manager.lookup_errors == [not_found_error]
        assert utils.get_agent_lookup_failure_counts(single_entity, failing_manager.lookup_errors) == (
            1,
            0,
            ["VENDOR_ERROR"],
        )

    def test_get_token_missing_header_raises_auth_failed(self) -> None:
        """Verify get_token raises AUTHENTICATION_FAILED when X-FeApi-Token is missing."""
        manager = make_manager()
        manager.session.get = MagicMock(return_value=make_response(200))

        with pytest.raises(
            FireEyeHXManagerError,
            match=r"^Authentication failed\. No X-FeApi-Token found\.$",
        ) as raised:
            manager.get_token()

        assert raised.value.error_type == utils.ErrorType.AUTHENTICATION_FAILED
        assert utils.classify_exception(raised.value) == (
            "AUTHENTICATION_FAILED",
            "FireEyeHXManagerError",
            None,
        )
