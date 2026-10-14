from types import SimpleNamespace

import pytest
from core.exceptions import VegaRateLimitException
from core.rate_limit import RateLimitController
from core.VegaManager import VegaManager, is_rate_limit_message


class DummySession:
    trust_env = False
    verify = True


def _manager():
    waits: list[int] = []
    manager = VegaManager(
        api_root="https://api.vega.io",
        access_key_id="kid",
        access_key="secret",
        session=DummySession(),
        rate_limiter=RateLimitController(sleeper=lambda seconds: waits.append(seconds)),
        sleeper=lambda seconds: waits.append(seconds),
    )
    manager._jwt = "token"
    return manager, waits


def test_is_rate_limit_message_matches_vega_graphql_body() -> None:
    assert is_rate_limit_message("Rate limit exceeded. Please retry after a brief wait.")
    assert is_rate_limit_message("too many requests")
    assert not is_rate_limit_message("Unknown field labels")


def test_graphql_http_200_rate_limit_waits_and_retries() -> None:
    manager, waits = _manager()
    payloads = [
        {"errors": [{"message": "Rate limit exceeded. Please retry after a brief wait."}]},
        {"data": {"getAlerts": {"alerts": [{"id": "a-1"}]}}},
    ]

    def _request(*_args, **_kwargs):
        return SimpleNamespace(json=lambda: payloads.pop(0), status_code=200)

    manager._request = _request
    data = manager.graphql("query Q { getAlerts { alerts { id } } }")
    assert data == {"getAlerts": {"alerts": [{"id": "a-1"}]}}
    assert waits == [2]


def test_graphql_http_200_rate_limit_gives_up_after_max_hits() -> None:
    manager, waits = _manager()

    def _request(*_args, **_kwargs):
        return SimpleNamespace(
            json=lambda: {"errors": [{"message": "Rate limit exceeded. Please retry after a brief wait."}]},
            status_code=200,
        )

    manager._request = _request
    with pytest.raises(VegaRateLimitException):
        manager.graphql("query Q { getAlerts { alerts { id } } }")
    assert waits == [2, 4, 6, 8, 10, 12, 14]
