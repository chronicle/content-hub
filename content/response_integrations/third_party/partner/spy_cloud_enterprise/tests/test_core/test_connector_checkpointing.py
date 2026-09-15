"""Tests for the connector's checkpoint safety and resumable-drain recovery.

Two failure modes are covered here, both observed in production:

1. A publish-date window ending at ``now`` returns 0 for records SpyCloud has
   published but not yet indexed, and the checkpoint then advances past them, so
   they can never be fetched again. The window must trail ``now``.
2. A modification drain resumed from a persisted cursor fails identically on
   every cycle once that cursor expires, and because a failed cycle persists no
   progress it retries the dead cursor indefinitely. The drain must recover.
"""

from __future__ import annotations

import json
import time
from datetime import datetime, timedelta, timezone

import pytest
import requests

from spy_cloud_enterprise.core import SpyCloudManager as manager_module
from spy_cloud_enterprise.core.CheckpointManager import (
    DEFAULT_INGESTION_LAG_MINUTES,
    CheckpointManager,
)
from spy_cloud_enterprise.core.SpyCloudManager import (
    MODIFICATION_MAX_CONSECUTIVE_FAILURES,
    WATCHLIST_MODIFICATION_CURSOR_KEY,
    WATCHLIST_MODIFICATION_CURSOR_SINCE_KEY,
    WATCHLIST_MODIFICATION_FAILURE_COUNT_KEY,
    WATCHLIST_MODIFICATION_LAST_RUN_DATE_KEY,
    WATCHLIST_MODIFICATION_WINDOW_UNTIL_KEY,
    SpyCloudManager,
)
from spy_cloud_enterprise.core.SpyCloudSDK import (
    APIClient,
    SpyCloudException,
    SpyCloudInvalidCursorException,
)

ISO = "%Y-%m-%dT%H:%M:%SZ"


def _parse(value: str) -> datetime:
    return datetime.strptime(value, ISO).replace(tzinfo=timezone.utc)


class _Logger:
    def __init__(self) -> None:
        self.messages: list[str] = []

    def _record(self, message: str) -> None:
        self.messages.append(str(message))

    info = warn = warning = error = _record


class _Siemplify:
    """Minimal stand-in for SiemplifyConnectorExecution's context-property API."""

    def __init__(self, timestamp: int = 0, context: dict | None = None) -> None:
        self.LOGGER = _Logger()
        self.script_name = "test"
        self._timestamp = timestamp
        self._context: dict[str, str] = dict(context or {})

    def fetch_timestamp(self, **_: object) -> int:
        return self._timestamp

    def save_timestamp(self, new_timestamp: int = 0, **_: object) -> None:
        self._timestamp = new_timestamp

    def get_connector_context_property(self, _identifier: str, key: str):
        return self._context.get(key)

    def set_connector_context_property(self, _identifier: str, key: str, value: str) -> None:
        self._context[key] = value


def _manager(siemplify: _Siemplify, severities: list[int] | None = None) -> SpyCloudManager:
    """Build a manager without running __init__ (which needs connector params)."""
    instance = object.__new__(SpyCloudManager)
    instance.siemplify = siemplify
    instance._context_identifier = "connector-1"
    instance.severities = severities if severities is not None else [20, 25, 30]
    instance.enable_compass = False
    instance._pending_context_writes = []
    instance._modification_drain_in_progress = False
    return instance


class TestIngestionLagBuffer:
    """The publish-date window must never extend to `now`."""

    def test_first_run_window_ends_behind_now(self) -> None:
        checkpoint_manager = CheckpointManager(_Siemplify(timestamp=0))
        since, until = checkpoint_manager.get_next_since_until()

        now = datetime.now(timezone.utc)
        lag_seconds = (now - _parse(until)).total_seconds()

        assert DEFAULT_INGESTION_LAG_MINUTES * 60 - 5 <= lag_seconds
        assert _parse(since) < _parse(until)

    def test_first_run_still_uses_the_full_lookback(self) -> None:
        checkpoint_manager = CheckpointManager(_Siemplify(timestamp=0))
        since, _ = checkpoint_manager.get_next_since_until()

        span_hours = (datetime.now(timezone.utc) - _parse(since)).total_seconds() / 3600
        assert 23.9 <= span_hours <= 24.1

    def test_records_published_just_before_the_last_cycle_stay_in_range(self) -> None:
        """Regression: a record published 1 minute ago must not fall behind `since`.

        Previously the checkpoint advanced to `now`, so the next window started
        after records that were published but not yet queryable.
        """
        cycle_ran_at = datetime.now(timezone.utc)
        siemplify = _Siemplify(timestamp=0)
        checkpoint_manager = CheckpointManager(siemplify)

        # Cycle 1 checkpoints at its (lagged) window end.
        _, until = checkpoint_manager.get_next_since_until()
        checkpoint_manager.save_checkpoint(checkpoint_manager.iso_to_epoch_ms(until))

        # A record published shortly before that cycle, indexed only afterwards.
        published_at = cycle_ran_at - timedelta(minutes=1)

        since_next, _ = checkpoint_manager.get_next_since_until()
        assert _parse(since_next) <= published_at.replace(microsecond=0)

    def test_window_is_empty_when_a_cycle_runs_inside_the_lag_interval(self) -> None:
        siemplify = _Siemplify(timestamp=0)
        checkpoint_manager = CheckpointManager(siemplify)

        _, until = checkpoint_manager.get_next_since_until()
        checkpoint_manager.save_checkpoint(checkpoint_manager.iso_to_epoch_ms(until))

        since_next, until_next = checkpoint_manager.get_next_since_until()
        assert _parse(since_next) >= _parse(until_next)

    def test_zero_lag_is_honored_for_callers_that_opt_out(self) -> None:
        checkpoint_manager = CheckpointManager(_Siemplify(timestamp=0), ingestion_lag_minutes=0)
        _, until = checkpoint_manager.get_next_since_until()

        lag_seconds = (datetime.now(timezone.utc) - _parse(until)).total_seconds()
        assert lag_seconds < 60


class TestInvalidCursorClassification:
    """A rejected cursor is recoverable and must be typed distinctly."""

    @staticmethod
    def _response(status_code: int, body: dict) -> requests.Response:
        response = requests.Response()
        response.status_code = status_code
        response.reason = "Bad Request"
        response.url = "https://api.spycloud.io/enterprise-v2/breach/data/watchlist"
        response._content = json.dumps(body).encode()
        return response

    @staticmethod
    def _client() -> APIClient:
        return APIClient("test-api-key", base_url="https://api.spycloud.io")

    def test_cursor_not_found_raises_invalid_cursor(self) -> None:
        response = self._response(
            400,
            {
                "errorType": "BadRequest",
                "errorMessage": "[BadRequest] Invalid parameter: 'cursor'. Cursor not found.",
            },
        )

        with pytest.raises(SpyCloudInvalidCursorException):
            self._client().validate_response(response, "Unable to get results")

    def test_unrelated_bad_request_stays_a_general_exception(self) -> None:
        response = self._response(
            400,
            {"errorType": "BadRequest", "errorMessage": "Invalid parameter: 'severity'."},
        )

        with pytest.raises(SpyCloudException) as exc_info:
            self._client().validate_response(response, "Unable to get results")
        assert not isinstance(exc_info.value, SpyCloudInvalidCursorException)

    def test_server_error_stays_a_general_exception(self) -> None:
        response = self._response(500, {"errorMessage": "cursor"})

        with pytest.raises(SpyCloudException) as exc_info:
            self._client().validate_response(response, "Unable to get results")
        assert not isinstance(exc_info.value, SpyCloudInvalidCursorException)


class _FakeBreachData:
    """Records the cursor each drain page was requested with."""

    def __init__(self, outcomes: list) -> None:
        self._outcomes = list(outcomes)
        self.calls: list[dict] = []

    def watchlist_page(self, **kwargs):
        self.calls.append(kwargs)
        outcome = self._outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


class _FakeSdk:
    def __init__(self, breach_data: _FakeBreachData) -> None:
        self.breach_data = breach_data


class TestExpiredCursorRecovery:
    """An expired persisted cursor must restart the chunk, not wedge the drain."""

    @staticmethod
    def _in_progress_context(cursor: str = "dead-cursor") -> dict:
        now = datetime.now(timezone.utc)
        return {
            WATCHLIST_MODIFICATION_WINDOW_UNTIL_KEY: now.strftime(ISO),
            WATCHLIST_MODIFICATION_CURSOR_SINCE_KEY: (now - timedelta(hours=1)).strftime(ISO),
            WATCHLIST_MODIFICATION_CURSOR_KEY: cursor,
        }

    def test_rejected_cursor_retries_the_chunk_without_it(self) -> None:
        siemplify = _Siemplify(context=self._in_progress_context())
        breach_data = _FakeBreachData([
            SpyCloudInvalidCursorException(
                "Unable to get results: 400 Client Error: Invalid parameter: 'cursor'. "
                "Cursor not found."
            ),
            ([{"document_id": "a"}], None),
        ])
        instance = _manager(siemplify)
        instance.sdk = _FakeSdk(breach_data)

        records = instance._drain_watchlist_modification(
            deadline_monotonic=manager_module.time.monotonic() + 30,
        )

        assert len(records) == 1
        assert breach_data.calls[0]["start_cursor"] == "dead-cursor"
        # The retry re-requests the same chunk start, with no cursor.
        assert breach_data.calls[1]["start_cursor"] is None
        assert breach_data.calls[1]["since_modification"] == breach_data.calls[0]["since_modification"]

    def test_repeated_cursor_rejection_stops_within_the_cycle(self) -> None:
        """The retry must be bounded so a cycle cannot spin on cursor resets."""
        siemplify = _Siemplify(context=self._in_progress_context())
        rejection = SpyCloudInvalidCursorException("Cursor not found.")
        breach_data = _FakeBreachData([
            rejection,
            ([{"document_id": "a"}], "next-cursor-1"),
            rejection,
            ([{"document_id": "b"}], "next-cursor-2"),
            rejection,
        ])
        instance = _manager(siemplify)
        instance.sdk = _FakeSdk(breach_data)

        records = instance._drain_watchlist_modification(
            deadline_monotonic=manager_module.time.monotonic() + 30,
        )

        # Returns what it managed to collect rather than raising or looping.
        assert len(records) == 2
        assert instance._modification_drain_in_progress is True

    def test_cursor_rejection_without_a_sent_cursor_propagates(self) -> None:
        """A chunk-start request sends no cursor, so this is not recoverable here."""
        siemplify = _Siemplify(context=self._in_progress_context(cursor=""))
        breach_data = _FakeBreachData([SpyCloudInvalidCursorException("Cursor not found.")])
        instance = _manager(siemplify)
        instance.sdk = _FakeSdk(breach_data)

        with pytest.raises(SpyCloudInvalidCursorException):
            instance._drain_watchlist_modification(
                deadline_monotonic=manager_module.time.monotonic() + 30,
            )


class TestDrainFailureCircuitBreaker:
    """A drain window that fails every cycle must eventually be abandoned."""

    @staticmethod
    def _context() -> dict:
        now = datetime.now(timezone.utc)
        return {
            WATCHLIST_MODIFICATION_WINDOW_UNTIL_KEY: now.strftime(ISO),
            WATCHLIST_MODIFICATION_CURSOR_SINCE_KEY: (now - timedelta(hours=1)).strftime(ISO),
            WATCHLIST_MODIFICATION_CURSOR_KEY: "dead-cursor",
            WATCHLIST_MODIFICATION_LAST_RUN_DATE_KEY: "2026-08-14",
        }

    def test_first_failures_only_increment_the_counter(self) -> None:
        siemplify = _Siemplify(context=self._context())
        instance = _manager(siemplify)

        instance._record_watchlist_modification_failure(SpyCloudException("boom"))

        assert siemplify._context[WATCHLIST_MODIFICATION_FAILURE_COUNT_KEY] == "1"
        assert siemplify._context[WATCHLIST_MODIFICATION_CURSOR_KEY] == "dead-cursor"

    def test_window_is_abandoned_at_the_failure_threshold(self) -> None:
        siemplify = _Siemplify(context=self._context())
        instance = _manager(siemplify)

        for _ in range(MODIFICATION_MAX_CONSECUTIVE_FAILURES):
            instance._record_watchlist_modification_failure(SpyCloudException("boom"))

        assert siemplify._context[WATCHLIST_MODIFICATION_WINDOW_UNTIL_KEY] == ""
        assert siemplify._context[WATCHLIST_MODIFICATION_CURSOR_KEY] == ""
        assert siemplify._context[WATCHLIST_MODIFICATION_CURSOR_SINCE_KEY] == ""
        assert siemplify._context[WATCHLIST_MODIFICATION_FAILURE_COUNT_KEY] == "0"
        # Backed off for the rest of the day rather than restarting immediately.
        today = datetime.now(timezone.utc).date().isoformat()
        assert siemplify._context[WATCHLIST_MODIFICATION_LAST_RUN_DATE_KEY] == today

    def test_abandoned_window_writes_persist_immediately(self) -> None:
        """Recovery state must not be deferred: a failing cycle may deliver nothing."""
        siemplify = _Siemplify(context=self._context())
        instance = _manager(siemplify)

        for _ in range(MODIFICATION_MAX_CONSECUTIVE_FAILURES):
            instance._record_watchlist_modification_failure(SpyCloudException("boom"))

        assert instance._pending_context_writes == []

    def test_success_clears_a_partial_failure_streak(self) -> None:
        siemplify = _Siemplify(context=self._context())
        instance = _manager(siemplify)

        instance._record_watchlist_modification_failure(SpyCloudException("boom"))
        instance._clear_watchlist_modification_failures()

        assert siemplify._context[WATCHLIST_MODIFICATION_FAILURE_COUNT_KEY] == "0"

    def test_corrupt_counter_value_does_not_break_recovery(self) -> None:
        context = self._context()
        context[WATCHLIST_MODIFICATION_FAILURE_COUNT_KEY] = "not-a-number"
        siemplify = _Siemplify(context=context)
        instance = _manager(siemplify)

        instance._record_watchlist_modification_failure(SpyCloudException("boom"))

        assert siemplify._context[WATCHLIST_MODIFICATION_FAILURE_COUNT_KEY] == "1"


class _CountingBreachData:
    """Serves a fixed record batch per publish-date chunk request."""

    def __init__(self, records_per_chunk: int = 1) -> None:
        self.calls: list[dict] = []
        self._records_per_chunk = records_per_chunk

    def watchlist(self, **kwargs):
        self.calls.append(kwargs)
        return [
            {"document_id": f"{kwargs['since']}-{i}"}
            for i in range(self._records_per_chunk)
        ]


class TestWatchlistPerCycleBound:
    """The publish-date pull must not drain a whole backlog into one package.

    Every packaged alert carries a full UDM event and runs ~10 KB on the wire, so
    a cycle that drained a 24-hour lookback (12 chunks) at once wrote tens of MB
    to stdout in a single return_package and the platform discarded all of it.
    The pull now takes a bounded slice and reports the boundary it reached, which
    is the only point the caller may checkpoint.
    """

    @staticmethod
    def _window(hours: int) -> tuple[str, str]:
        until = datetime.now(timezone.utc).replace(microsecond=0)
        return (until - timedelta(hours=hours)).strftime(ISO), until.strftime(ISO)

    def test_stops_at_the_chunk_cap_and_reports_the_reached_boundary(self) -> None:
        since, until = self._window(hours=24)
        siemplify = _Siemplify()
        instance = _manager(siemplify)
        instance.sdk = _FakeSdk(_CountingBreachData())

        records, reached_until = instance._run_watchlist(since=since, until=until)

        assert len(instance.sdk.breach_data.calls) == manager_module.WATCHLIST_MAX_CHUNKS_PER_CYCLE
        assert len(records) == manager_module.WATCHLIST_MAX_CHUNKS_PER_CYCLE
        # The untouched tail of the window must not be checkpointed over.
        assert reached_until != until
        assert _parse(reached_until) == _parse(since) + timedelta(
            hours=manager_module.MAX_WATCHLIST_WINDOW_HOURS
            * manager_module.WATCHLIST_MAX_CHUNKS_PER_CYCLE
        )

    def test_fully_drained_window_reports_until_unchanged(self) -> None:
        since, until = self._window(hours=manager_module.MAX_WATCHLIST_WINDOW_HOURS)
        siemplify = _Siemplify()
        instance = _manager(siemplify)
        instance.sdk = _FakeSdk(_CountingBreachData())

        _, reached_until = instance._run_watchlist(since=since, until=until)

        assert reached_until == until

    def test_expired_time_budget_leaves_the_checkpoint_unmoved(self) -> None:
        since, until = self._window(hours=24)
        siemplify = _Siemplify()
        instance = _manager(siemplify)
        instance.sdk = _FakeSdk(_CountingBreachData())

        records, reached_until = instance._run_watchlist(
            since=since,
            until=until,
            deadline_monotonic=time.monotonic() - 1,
        )

        assert instance.sdk.breach_data.calls == []
        assert records == []
        assert reached_until is None
