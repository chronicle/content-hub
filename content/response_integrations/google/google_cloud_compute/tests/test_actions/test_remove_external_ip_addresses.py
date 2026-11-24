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

"""Unit tests for GoogleCloudCompute – Remove External IP Addresses action."""
from __future__ import annotations

from TIPCommon.base.action import ExecutionState

from google_cloud_compute.actions import RemoveExternalIPAddresses
from google_cloud_compute.tests.common import (
    CONFIG,
    INSTANCE_RESOURCE_PATH,
    MOCK_DATA,

    FAR_FUTURE_DEADLINE_MS,
)
from google_cloud_compute.tests.core.product import GoogleCloudCompute
from google_cloud_compute.tests.core.session import GoogleCloudComputeSession
from integration_testing.common import set_is_first_run_to_true, set_is_first_run_to_false
from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata

_PARAMS_ALL_NICS: dict[str, object] = {
    "Resource Name": INSTANCE_RESOURCE_PATH,
    "Network Interfaces": "*",
}

_PARAMS_SPECIFIC_NIC: dict[str, object] = {
    "Resource Name": INSTANCE_RESOURCE_PATH,
    "Network Interfaces": "nic0",
}

_PARAMS_MISSING_RESOURCE: dict[str, object] = {
    "Network Interfaces": "*",
}


@set_metadata(integration_config=CONFIG, parameters=_PARAMS_ALL_NICS,
    input_context={"execution_deadline_unix_time_ms": FAR_FUTURE_DEADLINE_MS})
def test_remove_external_ip_all_nics_success(
    _script_session: GoogleCloudComputeSession,
    compute_product: GoogleCloudCompute,
    action_output: MockActionOutput,
) -> None:
    """Wildcard NIC selection on first run → removes external IPs → COMPLETED."""
    set_is_first_run_to_true()
    compute_product.set_instance(MOCK_DATA["instance"])
    # The instance has nic0 with stackType=IPV4_ONLY and one access config (External NAT).
    # The action deletes the access config. Operation is DONE synchronously.
    compute_product.set_operation(MOCK_DATA["operation_done"])

    RemoveExternalIPAddresses.main()

    assert action_output.results.execution_state == ExecutionState.COMPLETED
    assert action_output.results.result_value is True
    assert "Successfully removed external IP" in action_output.results.output_message


@set_metadata(integration_config=CONFIG, parameters=_PARAMS_SPECIFIC_NIC,
    input_context={"execution_deadline_unix_time_ms": FAR_FUTURE_DEADLINE_MS})
def test_remove_external_ip_specific_nic_success(
    _script_session: GoogleCloudComputeSession,
    compute_product: GoogleCloudCompute,
    action_output: MockActionOutput,
) -> None:
    """Specific NIC name → access config removed → COMPLETED, True."""
    set_is_first_run_to_true()
    compute_product.set_instance(MOCK_DATA["instance"])
    compute_product.set_operation(MOCK_DATA["operation_done"])

    RemoveExternalIPAddresses.main()

    assert action_output.results.execution_state == ExecutionState.COMPLETED
    assert action_output.results.result_value is True


@set_metadata(integration_config=CONFIG, parameters=_PARAMS_ALL_NICS,
    input_context={"execution_deadline_unix_time_ms": FAR_FUTURE_DEADLINE_MS})
def test_remove_external_ip_operations_still_running(
    _script_session: GoogleCloudComputeSession,
    compute_product: GoogleCloudCompute,
    action_output: MockActionOutput,
) -> None:
    """Operation RUNNING on first-run poll → IN_PROGRESS."""
    set_is_first_run_to_true()
    compute_product.set_instance(MOCK_DATA["instance"])
    compute_product.set_operation(MOCK_DATA["operation_running"])

    RemoveExternalIPAddresses.main()

    assert action_output.results.execution_state == ExecutionState.IN_PROGRESS


@set_metadata(integration_config=CONFIG, parameters=_PARAMS_MISSING_RESOURCE)
def test_remove_external_ip_missing_resource(
    _script_session: GoogleCloudComputeSession,
    _compute_product: GoogleCloudCompute,
    action_output: MockActionOutput,
) -> None:
    """No resource identification → FAILED."""
    set_is_first_run_to_true()

    RemoveExternalIPAddresses.main()

    assert action_output.results.execution_state == ExecutionState.FAILED


@set_metadata(integration_config=CONFIG, parameters=_PARAMS_ALL_NICS)
def test_remove_external_ip_api_error(
    _script_session: GoogleCloudComputeSession,
    compute_product: GoogleCloudCompute,
    action_output: MockActionOutput,
) -> None:
    """API error during get_instance → FAILED."""
    set_is_first_run_to_true()
    with compute_product.fail_requests():
        RemoveExternalIPAddresses.main()

    assert action_output.results.execution_state == ExecutionState.FAILED
    assert action_output.results.result_value is False
