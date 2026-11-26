# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import annotations

from TIPCommon.base.action import ExecutionState
from proofpoint_threat_protection.actions import (
    remove_entry_from_allow_list,
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
    "Successfully deleted entry in the allow list based on the provided criteria"
)
ERROR_MESSAGE = (
    "invalid cluster ID provided or credentials in the integration configuration."
)


@set_metadata(
    integration_config=common.CONFIG,
    parameters={
        "Cluster ID": "test_cluster",
        "IOC Type To Search": "Sender Hostname",
        "Value": "test.com",
    },
)
def test_remove_entry_from_allow_list_success(
    proofpoint_ctr: ProofpointThreatProtection,
    script_session: ProofpointThreatProtectionSession,
    action_output: MockActionOutput,
):
    """Test for successful Remove Entry From Allow List action."""
    proofpoint_ctr.cleanup_allow_list_entries()
    proofpoint_ctr.add_allow_list_entries(common.ALLOW_LIST_ENTRIES_JSON["entries"])

    remove_entry_from_allow_list.main()

    assert len(script_session.request_history) == 2
    assert SUCCESS_MESSAGE in action_output.results.output_message
    assert action_output.results.result_value is True
    assert action_output.results.execution_state == ExecutionState.COMPLETED
    assert len(proofpoint_ctr.get_allow_list_entries()) == 1


@set_metadata(
    integration_config=common.CONFIG,
    parameters={
        "Cluster ID": "invalid_cluster",
        "IOC Type To Search": "Sender Hostname",
        "Value": "test.com",
    },
)
def test_remove_entry_from_allow_list_invalid_cluster(
    action_output: MockActionOutput,
):
    """Test for Remove Entry From Allow List action with an invalid cluster ID."""
    remove_entry_from_allow_list.main()
    assert ERROR_MESSAGE in action_output.results.output_message
    assert action_output.results.result_value is False
    assert action_output.results.execution_state == ExecutionState.FAILED
