"""Unit tests for GoogleCloudCompute – Add Network Tags action."""
from __future__ import annotations


from TIPCommon.base.action import ExecutionState

from google_cloud_compute.actions import AddNetworkTags
from google_cloud_compute.tests.common import (
    CONFIG,
    INSTANCE_RESOURCE_PATH,
    MOCK_DATA,
    ZONE,
    INSTANCE_ID,

    FAR_FUTURE_DEADLINE_MS,
)
from google_cloud_compute.tests.core.product import GoogleCloudCompute
from google_cloud_compute.tests.core.session import GoogleCloudComputeSession
from integration_testing.common import set_is_first_run_to_true, set_is_first_run_to_false
from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata

_PARAMS_BY_RESOURCE: dict[str, object] = {
    "Resource Name": INSTANCE_RESOURCE_PATH,
    "Network Tags": "new-tag,another-tag",
}

_PARAMS_BY_ZONE_AND_ID: dict[str, object] = {
    "Instance Zone": ZONE,
    "Instance ID": INSTANCE_ID,
    "Network Tags": "new-tag",
}

_PARAMS_MISSING_RESOURCE: dict[str, object] = {
    "Network Tags": "some-tag",
}


@set_metadata(integration_config=CONFIG, parameters=_PARAMS_BY_RESOURCE,
    input_context={"execution_deadline_unix_time_ms": FAR_FUTURE_DEADLINE_MS})
def test_add_network_tags_first_run_success(
    _script_session: GoogleCloudComputeSession,
    compute_product: GoogleCloudCompute,
    action_output: MockActionOutput,
) -> None:
    """First run: fetch instance tags, issue setTags → operation DONE → COMPLETED."""
    set_is_first_run_to_true()
    compute_product.set_instance(MOCK_DATA["instance"])
    compute_product.set_operation(MOCK_DATA["operation_done"])

    AddNetworkTags.main()

    assert action_output.results.execution_state == ExecutionState.COMPLETED
    assert action_output.results.result_value is True
    assert "Successfully added network tags" in action_output.results.output_message


@set_metadata(integration_config=CONFIG, parameters=_PARAMS_BY_RESOURCE,
    input_context={"execution_deadline_unix_time_ms": FAR_FUTURE_DEADLINE_MS})
def test_add_network_tags_first_run_operation_running(
    _script_session: GoogleCloudComputeSession,
    compute_product: GoogleCloudCompute,
    action_output: MockActionOutput,
) -> None:
    """First run: operation is still RUNNING → action goes IN_PROGRESS."""
    set_is_first_run_to_true()
    compute_product.set_instance(MOCK_DATA["instance"])
    compute_product.set_operation(MOCK_DATA["operation_running"])

    AddNetworkTags.main()

    assert action_output.results.execution_state == ExecutionState.IN_PROGRESS


@set_metadata(integration_config=CONFIG, parameters=_PARAMS_MISSING_RESOURCE)
def test_add_network_tags_missing_resource(
    _script_session: GoogleCloudComputeSession,
    _compute_product: GoogleCloudCompute,
    action_output: MockActionOutput,
) -> None:
    """No resource identification params → FAILED."""
    set_is_first_run_to_true()

    AddNetworkTags.main()

    assert action_output.results.execution_state == ExecutionState.FAILED
    assert action_output.results.result_value is False


@set_metadata(integration_config=CONFIG, parameters=_PARAMS_BY_RESOURCE)
def test_add_network_tags_api_error(
    _script_session: GoogleCloudComputeSession,
    compute_product: GoogleCloudCompute,
    action_output: MockActionOutput,
) -> None:
    """API error → FAILED."""
    set_is_first_run_to_true()
    with compute_product.fail_requests():
        AddNetworkTags.main()

    assert action_output.results.execution_state == ExecutionState.FAILED
    assert action_output.results.result_value is False
