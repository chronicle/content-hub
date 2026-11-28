from __future__ import annotations

from typing import TYPE_CHECKING

from integration_testing.set_meta import set_metadata
from TIPCommon.base.action import ExecutionState

from huntbase.actions import list_pending_approvals

from .. import common

if TYPE_CHECKING:
    from integration_testing.platform.script_output import MockActionOutput

    from ..core.product import Huntbase


@set_metadata(integration_config=common.CONFIG, parameters={"Max Results": "1"})
def test_list_pending_approvals(huntbase: Huntbase, action_output: MockActionOutput) -> None:
    huntbase.proposals = [
        {"proposal_id": "p1", "summary": "Add values", "state": "pending_approval", "values_count": 3},
        {"proposal_id": "p2", "summary": "Add a domain", "state": "pending_approval"},
    ]

    list_pending_approvals.main()

    results = action_output.results
    assert results.execution_state == ExecutionState.COMPLETED
    assert results.result_value is True
    assert "1 pending approval(s)" in results.output_message
    data = results.json_output.json_result
    assert data["count"] == 1
    assert data["items"][0]["url"].endswith("proposal=p1&src=google_secops")


@set_metadata(integration_config=common.CONFIG)
def test_list_pending_approvals_empty(action_output: MockActionOutput) -> None:
    list_pending_approvals.main()

    assert action_output.results.result_value is False
    assert action_output.results.output_message == "No pending approvals in Huntbase."


@set_metadata(integration_config=common.CONFIG, parameters={"Max Results": "0"})
def test_list_pending_approvals_bad_limit(action_output: MockActionOutput) -> None:
    list_pending_approvals.main()

    assert action_output.results.execution_state == ExecutionState.FAILED
