from __future__ import annotations


from TIPCommon.base.action import ExecutionState
from proofpoint_threat_protection.actions import (
    get_allow_list_entries,
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

SUCCESS_MESSAGE = (
    "Successfully listed entries in the allow list based on the provided criteria."
)
NO_ENTRIES_MESSAGE = (
    "No entries were found in the allow list for the provided criteria."
)


@set_metadata(
    integration_config=common.CONFIG,
    parameters={
        "Cluster ID": "test_cluster",
        "IOC Type To Return": "All",
        "Max IOCs To Return": "100",
    },
)
def test_get_allow_list_entries_all_success(
    proofpoint_ctr: ProofpointThreatProtection,
    script_session: ProofpointThreatProtectionSession,
    action_output: MockActionOutput,
):
    """Test for successful Get Allow List Entries action with 'All' IOC type."""
    proofpoint_ctr.cleanup_allow_list_entries()
    proofpoint_ctr.add_allow_list_entries(common.ALLOW_LIST_ENTRIES_JSON["entries"])

    get_allow_list_entries.main()

    assert len(script_session.request_history) == 2
    assert action_output.results.output_message == SUCCESS_MESSAGE
    assert action_output.results.result_value is True
    assert action_output.results.execution_state == ExecutionState.COMPLETED


@set_metadata(
    integration_config=common.CONFIG,
    parameters={
        "Cluster ID": "test_cluster",
        "IOC Type To Return": "Sender Email Address",
        "Max IOCs To Return": "100",
    },
)
def test_get_allow_list_entries_filtered_success(
    proofpoint_ctr: ProofpointThreatProtection,
    script_session: ProofpointThreatProtectionSession,
    action_output: MockActionOutput,
):
    """Test for successful Get Allow List Entries action with a specific IOC type."""
    proofpoint_ctr.cleanup_allow_list_entries()
    proofpoint_ctr.add_allow_list_entries(common.ALLOW_LIST_ENTRIES_JSON["entries"])

    get_allow_list_entries.main()

    filtered_entries = [
        entry
        for entry in common.ALLOW_LIST_ENTRIES_JSON["entries"]
        if entry["attribute"] == "$from"
    ]

    assert len(script_session.request_history) == 2
    assert action_output.results.output_message == SUCCESS_MESSAGE
    assert action_output.results.result_value is True
    assert action_output.results.execution_state == ExecutionState.COMPLETED
    assert action_output.results.json_output.json_result == filtered_entries
