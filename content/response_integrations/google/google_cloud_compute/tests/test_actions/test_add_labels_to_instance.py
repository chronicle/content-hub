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

"""Unit tests for GoogleCloudCompute – Add Labels To Instance action."""
from __future__ import annotations

from TIPCommon.base.action import ExecutionState

from google_cloud_compute.actions import AddLabelsToInstance
from google_cloud_compute.tests.common import (
    CONFIG,
    INSTANCE_RESOURCE_PATH,
    MOCK_DATA,
)
from google_cloud_compute.tests.core.product import GoogleCloudCompute
from google_cloud_compute.tests.core.session import GoogleCloudComputeSession
from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata

_PARAMS_NEW_LABEL: dict[str, object] = {
    "Resource Name": INSTANCE_RESOURCE_PATH,
    "Instance Labels": "newkey:newvalue",
}

_PARAMS_DUPLICATE_LABEL: dict[str, object] = {
    "Resource Name": INSTANCE_RESOURCE_PATH,
    "Instance Labels": "env:test",  # "env" already exists on the canned instance
}

_PARAMS_INVALID_FORMAT: dict[str, object] = {
    "Resource Name": INSTANCE_RESOURCE_PATH,
    "Instance Labels": "badinput_no_colon",
}

_PARAMS_MISSING_RESOURCE: dict[str, object] = {
    "Instance Labels": "key:value",
}


@set_metadata(integration_config=CONFIG, parameters=_PARAMS_NEW_LABEL)
def test_add_labels_new_key_success(
    _script_session: GoogleCloudComputeSession,
    compute_product: GoogleCloudCompute,
    action_output: MockActionOutput,
) -> None:
    """Adding a brand new label → COMPLETED, result_value=True."""
    compute_product.set_instance(MOCK_DATA["instance"])
    compute_product.set_operation(MOCK_DATA["operation_done"])

    AddLabelsToInstance.main()

    assert action_output.results.execution_state == ExecutionState.COMPLETED
    assert action_output.results.result_value is True
    assert "successfully added" in action_output.results.output_message.lower()


@set_metadata(integration_config=CONFIG, parameters=_PARAMS_DUPLICATE_LABEL)
def test_add_labels_duplicate_key_not_added(
    _script_session: GoogleCloudComputeSession,
    compute_product: GoogleCloudCompute,
    action_output: MockActionOutput,
) -> None:
    """Duplicate label key already on instance → not added, result_value=False.

    ISSUE FINDER: The action silently skips duplicate labels and returns
    result_value=False with COMPLETED.  This is intentional per the action code
    but may surprise callers expecting True on partial success.
    """
    compute_product.set_instance(MOCK_DATA["instance"])
    compute_product.set_operation(MOCK_DATA["operation_done"])

    AddLabelsToInstance.main()

    assert action_output.results.execution_state == ExecutionState.COMPLETED
    assert action_output.results.result_value is False
    assert "already exist" in action_output.results.output_message.lower()


@set_metadata(integration_config=CONFIG, parameters=_PARAMS_MISSING_RESOURCE)
def test_add_labels_missing_resource_name(
    _script_session: GoogleCloudComputeSession,
    _compute_product: GoogleCloudCompute,
    action_output: MockActionOutput,
) -> None:
    """No resource identification params → FAILED."""
    AddLabelsToInstance.main()

    # GoogleCloudComputeResourceNameValidationError is caught by generic Exception handler → FAILED
    assert action_output.results.execution_state == ExecutionState.FAILED
    assert action_output.results.result_value is False


@set_metadata(integration_config=CONFIG, parameters=_PARAMS_NEW_LABEL)
def test_add_labels_api_error(
    _script_session: GoogleCloudComputeSession,
    compute_product: GoogleCloudCompute,
    action_output: MockActionOutput,
) -> None:
    """API failure on get_instance → FAILED."""
    with compute_product.fail_requests():
        AddLabelsToInstance.main()

    assert action_output.results.execution_state == ExecutionState.FAILED
    assert action_output.results.result_value is False
