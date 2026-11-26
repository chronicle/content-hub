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

"""Unit tests for GoogleCloudCompute – Ping action."""
from __future__ import annotations

from TIPCommon.base.action import ExecutionState

from google_cloud_compute.actions import Ping
from google_cloud_compute.tests.common import CONFIG
from google_cloud_compute.tests.core.product import GoogleCloudCompute
from google_cloud_compute.tests.core.session import GoogleCloudComputeSession
from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata


@set_metadata(integration_config=CONFIG)
def test_ping_success(
    _script_session: GoogleCloudComputeSession,
    compute_product: GoogleCloudCompute,
    action_output: MockActionOutput,
) -> None:
    """Ping returns COMPLETED when zones endpoint responds successfully."""
    compute_product.set_zones_response({"items": [{"name": "us-central1-a"}]})

    Ping.main()

    assert action_output.results.execution_state == ExecutionState.COMPLETED
    assert action_output.results.result_value is True
    assert "Successfully connected" in action_output.results.output_message


@set_metadata(integration_config=CONFIG)
def test_ping_api_error(
    _script_session: GoogleCloudComputeSession,
    compute_product: GoogleCloudCompute,
    action_output: MockActionOutput,
) -> None:
    """Ping returns FAILED when the API returns an error."""
    with compute_product.fail_requests():
        Ping.main()

    assert action_output.results.execution_state == ExecutionState.FAILED
    assert action_output.results.result_value is False
    assert "Failed to connect" in action_output.results.output_message
