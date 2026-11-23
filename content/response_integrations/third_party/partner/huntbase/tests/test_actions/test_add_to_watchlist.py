from __future__ import annotations

from typing import TYPE_CHECKING

from integration_testing.set_meta import set_metadata
from TIPCommon.base.action import ExecutionState

from huntbase.actions import add_to_watchlist

from .. import common
from ..conftest import MockEntity

if TYPE_CHECKING:
    from integration_testing.platform.script_output import MockActionOutput

    from ..core.product import Huntbase


def _entities() -> list[MockEntity]:
    return [
        MockEntity("203.0.113.10", "ADDRESS"),
        MockEntity("evil.example", "DOMAIN"),
        MockEntity("WS-0142", "HOSTNAME"),
    ]


@set_metadata(
    integration_config=common.CONFIG,
    entities=_entities(),
    parameters={"Watchlist": "SecOps escalations", "Additional Values": "bad:thing, 203.0.113.10"},
)
def test_add_to_watchlist_success(huntbase: Huntbase, action_output: MockActionOutput) -> None:
    huntbase.watchlists = [{"id": "w1", "name": "SecOps escalations"}]
    huntbase.watchlist_values["w1"] = ["evil.example"]

    add_to_watchlist.main()

    results = action_output.results
    assert results.execution_state == ExecutionState.COMPLETED
    assert results.result_value is True
    assert "1 added, 1 already present" in results.output_message
    assert "Rejected: bad:thing (unsupported value)" in results.output_message
    assert huntbase.watchlist_values["w1"] == ["evil.example", "203.0.113.10"]
    assert results.json_output.json_result["submitted"] == ["203.0.113.10", "evil.example", "bad:thing"]


@set_metadata(integration_config=common.CONFIG, entities=_entities(), parameters={"Watchlist": "Missing"})
def test_add_to_watchlist_unknown_list(huntbase: Huntbase, action_output: MockActionOutput) -> None:
    huntbase.watchlists = [{"id": "w1", "name": "SecOps escalations"}]

    add_to_watchlist.main()

    assert action_output.results.execution_state == ExecutionState.FAILED
    assert "Available watch lists: SecOps escalations" in action_output.results.output_message


@set_metadata(
    integration_config=common.CONFIG,
    entities=[MockEntity("WS-0142", "HOSTNAME")],
    parameters={"Watchlist": "w1"},
)
def test_add_to_watchlist_no_values(script_session: object, action_output: MockActionOutput) -> None:
    add_to_watchlist.main()

    assert action_output.results.execution_state == ExecutionState.FAILED
    assert "No IP, domain, URL or hash entities" in action_output.results.output_message
