from __future__ import annotations

import json

from TIPCommon.base.action import ExecutionState

from proofpoint_threat_protection.actions import (
    add_entry_to_block_list,
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

SUCCESS_MESSAGE = "Successfully added a new entry to the block list."

BLOCK_LIST_ITEM = {
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
        "Blocklist Item": json.dumps(BLOCK_LIST_ITEM),
    },
)
def test_add_entry_to_block_list_success(
    proofpoint_ctr: ProofpointThreatProtection,
    script_session: ProofpointThreatProtectionSession,
    action_output: MockActionOutput,
):
    """Test for successful Add Entry To Block List action."""
    proofpoint_ctr.cleanup_block_list_entries()
    add_entry_to_block_list.main()
    assert len(script_session.request_history) == 2
    assert action_output.results.output_message == SUCCESS_MESSAGE
    assert action_output.results.result_value is True
    assert action_output.results.execution_state == ExecutionState.COMPLETED


@set_metadata(
    integration_config=common.CONFIG,
    parameters={
        "Cluster ID": "invalid_cluster",
        "Blocklist Item": json.dumps(BLOCK_LIST_ITEM),
    },
)
def test_add_entry_to_block_list_invalid_cluster_id(
    proofpoint_ctr: ProofpointThreatProtection,
    script_session: ProofpointThreatProtectionSession,
    action_output: MockActionOutput,
):
    """Test for Add Entry To Block List action with an invalid cluster ID."""
    proofpoint_ctr.cleanup_block_list_entries()
    add_entry_to_block_list.main()

    assert len(script_session.request_history) == 2
    assert ERROR_MESSAGE in action_output.results.output_message
    assert action_output.results.result_value is False
    assert action_output.results.execution_state == ExecutionState.FAILED
