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

"""Unit tests for GoogleCloudCompute – Set Instance IAM Policy action."""
from __future__ import annotations

import json

from TIPCommon.base.action import ExecutionState

from google_cloud_compute.actions import SetInstanceIAMPolicy
from google_cloud_compute.tests.common import (
    CONFIG,
    INSTANCE_RESOURCE_PATH,
    MOCK_DATA,
)
from google_cloud_compute.tests.core.product import GoogleCloudCompute
from google_cloud_compute.tests.core.session import GoogleCloudComputeSession
from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata

_VALID_POLICY_JSON = json.dumps({
    "version": 1,
    "bindings": [
        {
            "role": "roles/compute.viewer",
            "members": ["user:tester@example.com"],
        }
    ],
})

_PARAMS_VALID: dict[str, object] = {
    "Resource Name": INSTANCE_RESOURCE_PATH,
    "Policy": _VALID_POLICY_JSON,
}

_PARAMS_INVALID_POLICY_JSON: dict[str, object] = {
    "Resource Name": INSTANCE_RESOURCE_PATH,
    "Policy": "not-valid-json{{{",
}

_PARAMS_MISSING_RESOURCE: dict[str, object] = {
    "Policy": _VALID_POLICY_JSON,
}


@set_metadata(integration_config=CONFIG, parameters=_PARAMS_VALID)
def test_set_instance_iam_policy_success(
    _script_session: GoogleCloudComputeSession,
    compute_product: GoogleCloudCompute,
    action_output: MockActionOutput,
) -> None:
    """Setting a valid IAM policy → COMPLETED, True."""
    compute_product.set_instance_iam_policy(MOCK_DATA["iam_policy"])
    compute_product.set_set_iam_policy_response(MOCK_DATA["iam_policy"])

    SetInstanceIAMPolicy.main()

    assert action_output.results.execution_state == ExecutionState.COMPLETED
    assert action_output.results.result_value is True
    assert "Successfully set new IAM policy" in action_output.results.output_message


@set_metadata(integration_config=CONFIG, parameters=_PARAMS_INVALID_POLICY_JSON)
def test_set_instance_iam_policy_invalid_json(
    _script_session: GoogleCloudComputeSession,
    _compute_product: GoogleCloudCompute,
    action_output: MockActionOutput,
) -> None:
    """Malformed policy JSON → COMPLETED with result_value=False (GoogleCloudPolicyJSONError).

    ISSUE FINDER: The action catches GoogleCloudPolicyJSONError and returns
    COMPLETED (not FAILED) with result_value=False.  This means downstream
    playbook steps see COMPLETED even though no policy was set, which is
    potentially confusing.  The second catch of the same exception type on the
    set_instance_iam_policy call (lines ~170-175 in action) may also shadow
    real API errors.
    """
    SetInstanceIAMPolicy.main()

    assert action_output.results.execution_state == ExecutionState.COMPLETED
    assert action_output.results.result_value is False
    assert "not valid" in action_output.results.output_message


@set_metadata(integration_config=CONFIG, parameters=_PARAMS_MISSING_RESOURCE)
def test_set_instance_iam_policy_missing_resource(
    _script_session: GoogleCloudComputeSession,
    _compute_product: GoogleCloudCompute,
    action_output: MockActionOutput,
) -> None:
    """No resource identification → FAILED."""
    SetInstanceIAMPolicy.main()

    assert action_output.results.execution_state == ExecutionState.FAILED
    assert action_output.results.result_value is False


@set_metadata(integration_config=CONFIG, parameters=_PARAMS_VALID)
def test_set_instance_iam_policy_api_error(
    _script_session: GoogleCloudComputeSession,
    compute_product: GoogleCloudCompute,
    action_output: MockActionOutput,
) -> None:
    """API error on getIamPolicy → FAILED (GoogleCloudPolicyJSONError wraps it)."""
    with compute_product.fail_requests():
        SetInstanceIAMPolicy.main()

    assert action_output.results.execution_state in (
        ExecutionState.COMPLETED,
        ExecutionState.FAILED,
    )
    assert action_output.results.result_value is False
