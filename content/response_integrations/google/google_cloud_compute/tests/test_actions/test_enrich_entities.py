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

"""Unit tests for GoogleCloudCompute – Enrich Entities action."""
from __future__ import annotations

from TIPCommon.base.action import ExecutionState, EntityTypesEnum

from google_cloud_compute.actions import EnrichEntities
from google_cloud_compute.tests.common import CONFIG, MOCK_DATA, ZONE
from google_cloud_compute.tests.core.product import GoogleCloudCompute
from google_cloud_compute.tests.core.session import GoogleCloudComputeSession
from integration_testing.common import create_entity
from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata

# Provide a far-future execution deadline so the timeout guard inside the action
# does not trigger during unit tests (default is epoch 0 which always fires).
_FAR_FUTURE_DEADLINE_MS: int = 9_999_999_999_999  # year ~2286

_ENTITY_IP = "10.128.0.2"
_ENTITY_IP_NOT_FOUND = "192.168.99.99"

_IP_ENTITY = create_entity(identifier=_ENTITY_IP, type_=EntityTypesEnum.ADDRESS)
_IP_ENTITY_NOT_FOUND = create_entity(
    identifier=_ENTITY_IP_NOT_FOUND, type_=EntityTypesEnum.ADDRESS
)

_PARAMS_AGGREGATED: dict[str, object] = {}
_PARAMS_WITH_ZONE: dict[str, object] = {"Instance Zone": ZONE}


@set_metadata(
    integration_config=CONFIG,
    parameters=_PARAMS_AGGREGATED,
    entities=[_IP_ENTITY],
    input_context={"execution_deadline_unix_time_ms": _FAR_FUTURE_DEADLINE_MS},
)
def test_enrich_entities_success(
    _script_session: GoogleCloudComputeSession,
    compute_product: GoogleCloudCompute,
    action_output: MockActionOutput,
) -> None:
    """Entity whose IP matches a NIC networkIP is enriched → COMPLETED, True."""
    compute_product.set_instances_aggregated(MOCK_DATA["instances_aggregated_response"])

    EnrichEntities.main()

    assert action_output.results.execution_state == ExecutionState.COMPLETED
    assert action_output.results.result_value is True
    assert _ENTITY_IP in action_output.results.output_message


@set_metadata(
    integration_config=CONFIG,
    parameters=_PARAMS_AGGREGATED,
    entities=[_IP_ENTITY_NOT_FOUND],
    input_context={"execution_deadline_unix_time_ms": _FAR_FUTURE_DEADLINE_MS},
)
def test_enrich_entities_no_match(
    _script_session: GoogleCloudComputeSession,
    compute_product: GoogleCloudCompute,
    action_output: MockActionOutput,
) -> None:
    """Entity IP not found in any instance → COMPLETED, result_value=False.

    ISSUE FINDER: ``get_instance_to_enrich_with`` has an off-by-one bug:
    when ``len(running_instances) == 1`` the function returns
    ``running_instances[1]`` (index 1) instead of ``running_instances[0]``,
    causing an IndexError for single-element lists.  The guard
    ``if len(running_instances) == 1: return running_instances[1]`` is
    unreachable logic and will raise IndexError at runtime.
    """
    compute_product.set_instances_aggregated(MOCK_DATA["instances_aggregated_response"])

    EnrichEntities.main()

    assert action_output.results.execution_state == ExecutionState.COMPLETED
    assert action_output.results.result_value is False
    assert "No entities were enriched" in action_output.results.output_message


@set_metadata(
    integration_config=CONFIG,
    parameters=_PARAMS_WITH_ZONE,
    entities=[_IP_ENTITY],
    input_context={"execution_deadline_unix_time_ms": _FAR_FUTURE_DEADLINE_MS},
)
def test_enrich_entities_with_zone_success(
    _script_session: GoogleCloudComputeSession,
    compute_product: GoogleCloudCompute,
    action_output: MockActionOutput,
) -> None:
    """Zone-scoped enrichment succeeds when instance matches entity IP."""
    compute_product.set_instances(MOCK_DATA["instances_by_zone_response"])

    EnrichEntities.main()

    assert action_output.results.execution_state == ExecutionState.COMPLETED
    assert action_output.results.result_value is True


@set_metadata(
    integration_config=CONFIG,
    parameters=_PARAMS_AGGREGATED,
    entities=[_IP_ENTITY],
    input_context={"execution_deadline_unix_time_ms": _FAR_FUTURE_DEADLINE_MS},
)
def test_enrich_entities_api_error(
    _script_session: GoogleCloudComputeSession,
    compute_product: GoogleCloudCompute,
    action_output: MockActionOutput,
) -> None:
    """API failure during instance list fetch → FAILED."""
    with compute_product.fail_requests():
        EnrichEntities.main()

    assert action_output.results.execution_state == ExecutionState.FAILED
    assert action_output.results.result_value is False


@set_metadata(
    integration_config=CONFIG,
    parameters=_PARAMS_AGGREGATED,
    entities=[],
    input_context={"execution_deadline_unix_time_ms": _FAR_FUTURE_DEADLINE_MS},
)
def test_enrich_entities_no_entities(
    _script_session: GoogleCloudComputeSession,
    compute_product: GoogleCloudCompute,
    action_output: MockActionOutput,
) -> None:
    """No target entities → COMPLETED, result_value=False, no enrichment attempted."""
    compute_product.set_instances_aggregated(MOCK_DATA["instances_aggregated_response"])

    EnrichEntities.main()

    assert action_output.results.execution_state == ExecutionState.COMPLETED
    assert action_output.results.result_value is False
