from __future__ import annotations

from TIPCommon.base.action import ExecutionState
from proofpoint_threat_protection.actions import (
    add_ioc_to_block_list,
)

from proofpoint_threat_protection.tests import common
from proofpoint_threat_protection.tests.core.product import (
    ProofpointThreatProtection,
)
from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata

SUCCESS_MESSAGE = "Successfully added new entries to the block list."
INVALID_CLUSTER_MESSAGE = (
    "invalid cluster ID provided or credentials in the integration configuration."
)


@set_metadata(
    integration_config=common.CONFIG,
    parameters={
        "Cluster ID": "test_cluster",
        "Recipient Email Address": "recipient@example.com",
        "Sender IP Address": "1.2.3.4,5.6.7.8",
        "Comment": "Test comment",
    },
)
def test_add_ioc_to_block_list_success(
    proofpoint_ctr: ProofpointThreatProtection,
    action_output: MockActionOutput,
):
    """Test for successful Add IOC To Block List action."""
    proofpoint_ctr.cleanup_block_list_entries()

    add_ioc_to_block_list.main()

    assert action_output.results.output_message == SUCCESS_MESSAGE
    assert action_output.results.result_value is True
    assert action_output.results.execution_state == ExecutionState.COMPLETED


@set_metadata(
    integration_config=common.CONFIG,
    parameters={
        "Cluster ID": "invalid_cluster",
        "Sender Hostname": "some.host.com",
    },
)
def test_add_ioc_to_block_list_invalid_cluster(
    proofpoint_ctr: ProofpointThreatProtection,
    action_output: MockActionOutput,
):
    """Test for Add IOC To Block List action with an invalid cluster ID."""
    proofpoint_ctr.cleanup_block_list_entries()
    add_ioc_to_block_list.main()

    assert INVALID_CLUSTER_MESSAGE in action_output.results.output_message
    assert action_output.results.result_value is False
    assert action_output.results.execution_state == ExecutionState.FAILED
