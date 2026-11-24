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

"""Unit tests for GoogleCloudCompute – Remove Network Tags action."""
from __future__ import annotations

from TIPCommon.base.action import ExecutionState

from google_cloud_compute.actions import RemoveNetworkTags
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

# The canned instance has tags ["http-server", "https-server"].
_PARAMS_REMOVE_EXISTING: dict[str, object] = {
    "Resource Name": INSTANCE_RESOURCE_PATH,
    "Network Tags": "http-server",
}

_PARAMS_REMOVE_NON_EXISTING: dict[str, object] = {
    "Resource Name": INSTANCE_RESOURCE_PATH,
    "Network Tags": "tag-that-does-not-exist",
}

_PARAMS_MISSING_RESOURCE: dict[str, object] = {
    "Network Tags": "http-server",
}


@set_metadata(integration_config=CONFIG, parameters=_PARAMS_REMOVE_EXISTING,
    input_context={"execution_deadline_unix_time_ms": FAR_FUTURE_DEADLINE_MS})
def test_remove_network_tags_success(
    _script_session: GoogleCloudComputeSession,
    compute_product: GoogleCloudCompute,
    action_output: MockActionOutput,
) -> None:
    """Removing an existing tag on first run → COMPLETED, True."""
    set_is_first_run_to_true()
    compute_product.set_instance(MOCK_DATA["instance"])
    compute_product.set_operation(MOCK_DATA["operation_done"])

    RemoveNetworkTags.main()

    assert action_output.results.execution_state == ExecutionState.COMPLETED
    assert action_output.results.result_value is True
    assert "Successfully removed network tags" in action_output.results.output_message


@set_metadata(integration_config=CONFIG, parameters=_PARAMS_REMOVE_NON_EXISTING,
    input_context={"execution_deadline_unix_time_ms": FAR_FUTURE_DEADLINE_MS})
def test_remove_network_tags_non_existing_tag_still_succeeds(
    _script_session: GoogleCloudComputeSession,
    compute_product: GoogleCloudCompute,
    action_output: MockActionOutput,
) -> None:
    """Removing a tag that does not exist is a no-op → COMPLETED.

    ISSUE FINDER: The set difference logic silently produces an empty list when
    the tag to remove is not present. The action still calls setTags with the
    same tag list, which may be surprising. No explicit 'tag not found' message
    is returned to the caller.
    """
    set_is_first_run_to_true()
    compute_product.set_instance(MOCK_DATA["instance"])
    compute_product.set_operation(MOCK_DATA["operation_done"])

    RemoveNetworkTags.main()

    assert action_output.results.execution_state == ExecutionState.COMPLETED
    # result_value may be True (operation succeeded) even if no tags were removed
    assert action_output.results.result_value is True


@set_metadata(integration_config=CONFIG, parameters=_PARAMS_REMOVE_EXISTING,
    input_context={"execution_deadline_unix_time_ms": FAR_FUTURE_DEADLINE_MS})
def test_remove_network_tags_operation_running(
    _script_session: GoogleCloudComputeSession,
    compute_product: GoogleCloudCompute,
    action_output: MockActionOutput,
) -> None:
    """Operation still RUNNING → IN_PROGRESS."""
    set_is_first_run_to_true()
    compute_product.set_instance(MOCK_DATA["instance"])
    compute_product.set_operation(MOCK_DATA["operation_running"])

    RemoveNetworkTags.main()

    assert action_output.results.execution_state == ExecutionState.IN_PROGRESS


@set_metadata(integration_config=CONFIG, parameters=_PARAMS_MISSING_RESOURCE)
def test_remove_network_tags_missing_resource(
    _script_session: GoogleCloudComputeSession,
    _compute_product: GoogleCloudCompute,
    action_output: MockActionOutput,
) -> None:
    """No resource identification → FAILED."""
    set_is_first_run_to_true()

    RemoveNetworkTags.main()

    assert action_output.results.execution_state == ExecutionState.FAILED


@set_metadata(integration_config=CONFIG, parameters=_PARAMS_REMOVE_EXISTING)
def test_remove_network_tags_api_error(
    _script_session: GoogleCloudComputeSession,
    compute_product: GoogleCloudCompute,
    action_output: MockActionOutput,
) -> None:
    """API error → FAILED."""
    set_is_first_run_to_true()
    with compute_product.fail_requests():
        RemoveNetworkTags.main()

    assert action_output.results.execution_state == ExecutionState.FAILED
