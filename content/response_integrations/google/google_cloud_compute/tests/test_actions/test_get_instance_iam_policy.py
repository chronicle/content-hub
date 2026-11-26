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

"""Unit tests for GoogleCloudCompute – Get Instance IAM Policy action."""
from __future__ import annotations

from TIPCommon.base.action import ExecutionState

from google_cloud_compute.actions import GetInstanceIAMPolicy
from google_cloud_compute.tests.common import (
    CONFIG,
    INSTANCE_RESOURCE_PATH,
    MOCK_DATA,
    ZONE,
    INSTANCE_ID,
)
from google_cloud_compute.tests.core.product import GoogleCloudCompute
from google_cloud_compute.tests.core.session import GoogleCloudComputeSession
from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata

_PARAMS_BY_RESOURCE: dict[str, object] = {
    "Resource Name": INSTANCE_RESOURCE_PATH,
}

_PARAMS_BY_ZONE_AND_ID: dict[str, object] = {
    "Instance Zone": ZONE,
    "Instance ID": INSTANCE_ID,
}

_PARAMS_MISSING_BOTH: dict[str, object] = {}


@set_metadata(integration_config=CONFIG, parameters=_PARAMS_BY_RESOURCE)
def test_get_instance_iam_policy_success(
    _script_session: GoogleCloudComputeSession,
    compute_product: GoogleCloudCompute,
    action_output: MockActionOutput,
) -> None:
    """Fetch IAM policy by resource name → COMPLETED, True."""
    compute_product.set_instance_iam_policy(MOCK_DATA["iam_policy"])

    GetInstanceIAMPolicy.main()

    assert action_output.results.execution_state == ExecutionState.COMPLETED
    assert action_output.results.result_value is True
    assert "IAM policy was fetched successfully" in action_output.results.output_message


@set_metadata(integration_config=CONFIG, parameters=_PARAMS_BY_ZONE_AND_ID)
def test_get_instance_iam_policy_by_zone_and_id_success(
    _script_session: GoogleCloudComputeSession,
    compute_product: GoogleCloudCompute,
    action_output: MockActionOutput,
) -> None:
    """Fetch IAM policy by zone+ID → COMPLETED, True."""
    compute_product.set_instance_iam_policy(MOCK_DATA["iam_policy"])

    GetInstanceIAMPolicy.main()

    assert action_output.results.execution_state == ExecutionState.COMPLETED
    assert action_output.results.result_value is True


@set_metadata(integration_config=CONFIG, parameters=_PARAMS_MISSING_BOTH)
def test_get_instance_iam_policy_missing_params(
    _script_session: GoogleCloudComputeSession,
    _compute_product: GoogleCloudCompute,
    action_output: MockActionOutput,
) -> None:
    """No resource identification → FAILED."""
    GetInstanceIAMPolicy.main()

    assert action_output.results.execution_state == ExecutionState.FAILED
    assert action_output.results.result_value is False


@set_metadata(integration_config=CONFIG, parameters=_PARAMS_BY_RESOURCE)
def test_get_instance_iam_policy_api_error(
    _script_session: GoogleCloudComputeSession,
    compute_product: GoogleCloudCompute,
    action_output: MockActionOutput,
) -> None:
    """API error → FAILED."""
    with compute_product.fail_requests():
        GetInstanceIAMPolicy.main()

    assert action_output.results.execution_state == ExecutionState.FAILED
    assert action_output.results.result_value is False
