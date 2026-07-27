"""In-memory fake of ``ciaops.pollers.drp.DRPPoller`` used by tests.

The DRP integration goes through ``GIBConnector.init_action_poller`` to obtain a
poller object exposing four methods that the production code calls:

- ``send_request(endpoint, params=..., method=..., json=...)``
- ``search_feed_by_id(feed_id=...)``
- ``get_seq_update_dict(date=..., collection_name=...)``
- ``create_update_generator(collection_name=..., sequpdate=..., ...)``

This class records every invocation on ``calls`` so individual tests can
assert on ordering, parameters, and counts (mirroring the request_history
exposed by ``MockSession`` in the Telegram tests). Behaviour for each
method is fully programmable via ``set_*`` helpers; an unset response
field defaults to a benign empty value so tests don't have to wire up
endpoints they don't exercise.
"""

from __future__ import annotations

import contextlib
import dataclasses
from typing import Any, Callable, Iterable


@dataclasses.dataclass(slots=True)
class PollerCall:
    """A single recorded call against the fake poller."""

    method: str
    args: tuple
    kwargs: dict


@dataclasses.dataclass(slots=True)
class FakePortion:
    """Minimal stand-in for a ciaops ``Parser`` portion."""

    events: list[dict]
    sequpdate: int | None = None

    def parse_portion(self) -> list[dict]:
        return list(self.events)


@dataclasses.dataclass(slots=True)
class FakeFeedParser:
    """Minimal stand-in for what ``DRPPoller.search_feed_by_id`` returns."""

    raw_dict: dict


class FakeDRPPoller:
    """Test double for ``ciaops.pollers.drp.DRPPoller``.

    Records every call made by production code so tests can assert on the
    request shape (endpoint, method, payload) just like the Telegram tests
    inspect ``script_session.request_history``.
    """

    def __init__(self) -> None:
        self.calls: list[PollerCall] = []
        self._send_request_response: Any = None
        self._send_request_side_effect: Callable[..., Any] | None = None
        self._search_feed_response: FakeFeedParser | None = None
        self._search_feed_side_effect: Callable[..., Any] | None = None
        self._seq_update_dict: dict[str, int] = {"violation/list": 1700000000000000}
        self._update_portions: list[FakePortion] = []
        self._fail_requests: bool = False
        self._fail_message: str = "Simulated DRP API failure"

    # -- response programming helpers --------------------------------------

    def set_send_request_response(self, response: Any) -> None:
        self._send_request_response = response

    def set_send_request_side_effect(self, fn: Callable[..., Any]) -> None:
        self._send_request_side_effect = fn

    def set_search_feed_response(self, raw_dict: dict) -> None:
        self._search_feed_response = FakeFeedParser(raw_dict=raw_dict)

    def set_search_feed_side_effect(self, fn: Callable[..., Any]) -> None:
        self._search_feed_side_effect = fn

    def set_seq_update_dict(self, mapping: dict[str, int]) -> None:
        self._seq_update_dict = dict(mapping)

    def set_update_portions(self, portions: Iterable[FakePortion]) -> None:
        self._update_portions = list(portions)

    @contextlib.contextmanager
    def fail_requests(self, message: str = "Simulated DRP API failure"):
        """Context manager: every API call raises ``Exception`` while active."""
        previous_state = self._fail_requests
        previous_message = self._fail_message
        self._fail_requests = True
        self._fail_message = message
        try:
            yield
        finally:
            self._fail_requests = previous_state
            self._fail_message = previous_message

    # -- DRPPoller-shaped surface -----------------------------------------

    def set_verify(self, verify: bool) -> None:
        self.calls.append(PollerCall("set_verify", (verify,), {}))

    def set_keys(self, collection_name: str, keys: dict) -> None:
        self.calls.append(PollerCall("set_keys", (), {"collection_name": collection_name, "keys": keys}))

    def send_request(
        self,
        endpoint: str,
        params: Any | None = None,
        method: str = "GET",
        json: Any | None = None,
        **kwargs: Any,
    ) -> Any:
        call_kwargs = {"params": params, "method": method, "json": json}
        call_kwargs.update(kwargs)
        self.calls.append(PollerCall("send_request", (endpoint,), call_kwargs))
        if self._fail_requests:
            raise Exception(self._fail_message)
        if self._send_request_side_effect is not None:
            return self._send_request_side_effect(endpoint=endpoint, params=params, method=method, json=json, **kwargs)
        return self._send_request_response

    def search_feed_by_id(self, feed_id: str) -> FakeFeedParser:
        self.calls.append(PollerCall("search_feed_by_id", (), {"feed_id": feed_id}))
        if self._fail_requests:
            raise Exception(self._fail_message)
        if self._search_feed_side_effect is not None:
            return self._search_feed_side_effect(feed_id=feed_id)
        if self._search_feed_response is None:
            return FakeFeedParser(raw_dict={})
        return self._search_feed_response

    def get_seq_update_dict(
        self,
        date: str | None = None,
        collection_name: str | None = None,
        **kwargs: Any,
    ) -> dict[str, int]:
        self.calls.append(
            PollerCall(
                "get_seq_update_dict",
                (),
                {"date": date, "collection_name": collection_name, **kwargs},
            )
        )
        if self._fail_requests:
            raise Exception(self._fail_message)
        if collection_name is not None:
            return {collection_name: self._seq_update_dict.get(collection_name, 1)}
        return dict(self._seq_update_dict)

    def create_update_generator(
        self,
        collection_name: str,
        sequpdate: int | str | None = None,
        **kwargs: Any,
    ):
        self.calls.append(
            PollerCall(
                "create_update_generator",
                (),
                {"collection_name": collection_name, "sequpdate": sequpdate, **kwargs},
            )
        )
        if self._fail_requests:
            raise Exception(self._fail_message)
        return iter(list(self._update_portions))

    # -- inspection helpers used by tests ---------------------------------

    def calls_to(self, method: str) -> list[PollerCall]:
        return [c for c in self.calls if c.method == method]

    def last_call(self, method: str | None = None) -> PollerCall | None:
        if method is None:
            return self.calls[-1] if self.calls else None
        matching = self.calls_to(method)
        return matching[-1] if matching else None
