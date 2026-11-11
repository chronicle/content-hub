from __future__ import annotations

import json

from TIPCommon.base.action import ExecutionState
from proofpoint_threat_protection.actions import (
    add_entry_to_allow_list,
)

from proofpoint_threat_protection.tests import common
from proofpoint_threat_protection.tests.core.product import (
    ProofpointThreatProtection,
)
from proofpoint_threat_protection.tests.core.session import (
    ProofpointThreatProtectionSession,
)
from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata

SUCCESS_MESSAGE = "Successfully added a new entry to the allow list."

ALLOW_LIST_ITEM = {
    "attribute": "$host",
    "operator": "equal",
    "value": "koko.com",
    "comment": "<comment>",
}

ERROR_MESSAGE = (
    "invalid cluster ID provided or credentials in the integration configuration."
)


@set_metadata(
    integration_config=common.CONFIG,
    parameters={
        "Cluster ID": "test_cluster",
        "Allowlist Item": json.dumps(ALLOW_LIST_ITEM),
    },
)
def test_add_entry_to_allow_list_success(
    proofpoint_ctr: ProofpointThreatProtection,
    script_session: ProofpointThreatProtectionSession,
    action_output: MockActionOutput,
):
    """Test for successful Add Entry To Allow List action."""
    proofpoint_ctr.cleanup_allow_list_entries()

    add_entry_to_allow_list.main()

    assert len(script_session.request_history) == 2
    assert action_output.results.output_message == SUCCESS_MESSAGE
    assert action_output.results.result_value is True
    assert action_output.results.execution_state == ExecutionState.COMPLETED
    allow_list = proofpoint_ctr.get_allow_list_entries()
    assert len(allow_list) == 1
    expected_item = ALLOW_LIST_ITEM.copy()
    expected_item["action"] = "add"
    assert allow_list[0] == expected_item


@set_metadata(
    integration_config=common.CONFIG,
    parameters={
        "Cluster ID": "invalid_cluster",
        "Allowlist Item": json.dumps(ALLOW_LIST_ITEM),
    },
)
def test_add_entry_to_allow_list_invalid_cluster_id(
    proofpoint_ctr: ProofpointThreatProtection,
    script_session: ProofpointThreatProtectionSession,
    action_output: MockActionOutput,
):
    """Test for Add Entry To Allow List action with an invalid cluster ID."""
    proofpoint_ctr.cleanup_allow_list_entries()

    add_entry_to_allow_list.main()

    assert len(script_session.request_history) == 2
    assert ERROR_MESSAGE in action_output.results.output_message
    assert action_output.results.result_value is False
    assert action_output.results.execution_state == ExecutionState.FAILED
