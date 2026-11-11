from __future__ import annotations

from TIPCommon.base.action import ExecutionState
from proofpoint_threat_protection.actions import (
    remove_entry_from_block_list,
)

from proofpoint_threat_protection.tests import common
from proofpoint_threat_protection.tests.core.product import (
    ProofpointThreatProtection,
)
from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata

SUCCESS_MESSAGE = (
    "Successfully deleted entry in the block list based on the provided criteria"
)

ERROR_MESSAGE = (
    "invalid cluster ID provided or credentials in the integration configuration."
)


@set_metadata(
    integration_config=common.CONFIG,
    parameters={
        "Cluster ID": "test_cluster",
        "IOC Type To Search": "Sender Hostname",
        "Value": "koko.com",
    },
)
def test_remove_entry_from_block_list_success(
    proofpoint_ctr: ProofpointThreatProtection,
    action_output: MockActionOutput,
):
    """Test for successful Remove Entry From Block List action."""
    proofpoint_ctr.cleanup_block_list_entries()
    proofpoint_ctr.add_block_list_entries(common.BLOCK_LIST_ENTRIES_JSON["entries"])

    remove_entry_from_block_list.main()

    assert SUCCESS_MESSAGE in action_output.results.output_message
    assert action_output.results.result_value is True
    assert action_output.results.execution_state == ExecutionState.COMPLETED
    assert len(proofpoint_ctr.get_block_list_entries()) == 1


@set_metadata(
    integration_config=common.CONFIG,
    parameters={
        "Cluster ID": "invalid_cluster",
        "IOC Type To Search": "Sender Hostname",
        "Value": "test.com",
    },
)
def test_remove_entry_from_block_list_invalid_cluster(
    action_output: MockActionOutput,
):
    """Test for Remove Entry From Block List action with an invalid cluster ID."""
    remove_entry_from_block_list.main()
    assert ERROR_MESSAGE in action_output.results.output_message
    assert action_output.results.result_value is False
    assert action_output.results.execution_state == ExecutionState.FAILED
