from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import pytest
from integration_testing.set_meta import set_metadata
from TIPCommon.base.action import ExecutionState

from huntbase.actions import ping

from .. import common

if TYPE_CHECKING:
    from integration_testing.platform.script_output import MockActionOutput

    from ..core.product import Huntbase
    from ..core.session import HuntbaseSession


@set_metadata(integration_config=common.CONFIG)
def test_ping_success(script_session: HuntbaseSession, action_output: MockActionOutput) -> None:
    ping.main()

    assert action_output.results.execution_state == ExecutionState.COMPLETED
    assert action_output.results.result_value is True
    assert action_output.results.output_message == ping.SUCCESS_MESSAGE
    assert len(script_session.request_history) == 1
    request = script_session.request_history[0].request
    assert request.url.path == "/api/v1/access/vocabulary"
    assert request.headers["Authorization"] == "Bearer hb_pat_test_key"


@set_metadata(integration_config=common.CONFIG)
def test_ping_bad_key(huntbase: Huntbase, action_output: MockActionOutput) -> None:
    huntbase.fail("ping", 401)

    ping.main()

    assert action_output.results.execution_state == ExecutionState.FAILED
    assert action_output.results.result_value is False
    assert action_output.results.output_message.startswith(ping.ERROR_MESSAGE)
    assert "rejected the API key" in action_output.results.output_message
    assert "hb_pat_test_key" not in action_output.results.output_message


@set_metadata(integration_config=common.CONFIG | {"API Root": "not a url"})
def test_ping_invalid_api_root(action_output: MockActionOutput) -> None:
    ping.main()

    assert action_output.results.execution_state == ExecutionState.FAILED
    assert "must be a valid https:// URL" in action_output.results.output_message


@set_metadata(integration_config=common.CONFIG)
def test_ping_closes_session(
    script_session: HuntbaseSession,
    action_output: MockActionOutput,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    closed = MagicMock()
    monkeypatch.setattr(script_session, "close", closed)

    ping.main()

    assert action_output.results.execution_state == ExecutionState.COMPLETED
    closed.assert_called_once()


@set_metadata(integration_config=common.CONFIG)
def test_ping_closes_session_on_failure(
    huntbase: Huntbase,
    script_session: HuntbaseSession,
    action_output: MockActionOutput,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    huntbase.fail("ping", 401)
    closed = MagicMock()
    monkeypatch.setattr(script_session, "close", closed)

    ping.main()

    assert action_output.results.execution_state == ExecutionState.FAILED
    closed.assert_called_once()
