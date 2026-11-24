"""Unit tests for GoogleCloudCompute – Add IP To Firewall Rule action."""
from __future__ import annotations

from TIPCommon.base.action import ExecutionState

from google_cloud_compute.actions import AddIPToFirewallRule
from google_cloud_compute.tests.common import (
    CONFIG,
    FIREWALL_RESOURCE_PATH,
    MOCK_DATA,

    FAR_FUTURE_DEADLINE_MS,
)
from google_cloud_compute.tests.core.product import GoogleCloudCompute
from google_cloud_compute.tests.core.session import GoogleCloudComputeSession
from integration_testing.common import set_is_first_run_to_true, set_is_first_run_to_false
from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata

_PARAMS_SOURCE_TYPE: dict[str, object] = {
    "Resource Name": FIREWALL_RESOURCE_PATH,
    "IP Ranges": "1.2.3.4/32,5.6.7.8/32",
    "Type": "SOURCE",
}

_PARAMS_DESTINATION_TYPE: dict[str, object] = {
    "Resource Name": FIREWALL_RESOURCE_PATH,
    "IP Ranges": "192.168.10.0/24",
    "Type": "DESTINATION",
}

_PARAMS_MISSING_RESOURCE: dict[str, object] = {
    "IP Ranges": "1.2.3.4/32",
    "Type": "SOURCE",
}

_PARAMS_INVALID_TYPE: dict[str, object] = {
    "Resource Name": FIREWALL_RESOURCE_PATH,
    "IP Ranges": "1.2.3.4/32",
    "Type": "INVALID_TYPE_VALUE",
}


@set_metadata(integration_config=CONFIG, parameters=_PARAMS_SOURCE_TYPE,
    input_context={"execution_deadline_unix_time_ms": FAR_FUTURE_DEADLINE_MS})
def test_add_ip_source_success(
    _script_session: GoogleCloudComputeSession,
    compute_product: GoogleCloudCompute,
    action_output: MockActionOutput,
) -> None:
    """Adding source IPs on first run → patch operation DONE → COMPLETED."""
    set_is_first_run_to_true()
    compute_product.set_firewall_rule(MOCK_DATA["firewall_rule"])
    compute_product.set_operation(MOCK_DATA["operation_done"])

    AddIPToFirewallRule.main()

    assert action_output.results.execution_state == ExecutionState.COMPLETED
    assert action_output.results.result_value is True
    assert "Successfully updated firewall rule" in action_output.results.output_message


@set_metadata(integration_config=CONFIG, parameters=_PARAMS_DESTINATION_TYPE,
    input_context={"execution_deadline_unix_time_ms": FAR_FUTURE_DEADLINE_MS})
def test_add_ip_destination_success(
    _script_session: GoogleCloudComputeSession,
    compute_product: GoogleCloudCompute,
    action_output: MockActionOutput,
) -> None:
    """Adding destination IPs → COMPLETED, True."""
    set_is_first_run_to_true()
    compute_product.set_firewall_rule(MOCK_DATA["firewall_rule_with_destination"])
    compute_product.set_operation(MOCK_DATA["operation_done"])

    AddIPToFirewallRule.main()

    assert action_output.results.execution_state == ExecutionState.COMPLETED
    assert action_output.results.result_value is True


@set_metadata(integration_config=CONFIG, parameters=_PARAMS_SOURCE_TYPE,
    input_context={"execution_deadline_unix_time_ms": FAR_FUTURE_DEADLINE_MS})
def test_add_ip_operation_running(
    _script_session: GoogleCloudComputeSession,
    compute_product: GoogleCloudCompute,
    action_output: MockActionOutput,
) -> None:
    """Operation RUNNING → IN_PROGRESS."""
    set_is_first_run_to_true()
    compute_product.set_firewall_rule(MOCK_DATA["firewall_rule"])
    compute_product.set_operation(MOCK_DATA["operation_running"])

    AddIPToFirewallRule.main()

    assert action_output.results.execution_state == ExecutionState.IN_PROGRESS


@set_metadata(integration_config=CONFIG, parameters=_PARAMS_MISSING_RESOURCE)
def test_add_ip_missing_resource(
    _script_session: GoogleCloudComputeSession,
    _compute_product: GoogleCloudCompute,
    action_output: MockActionOutput,
) -> None:
    """Missing both resource name and firewall rule → FAILED."""
    set_is_first_run_to_true()

    AddIPToFirewallRule.main()

    assert action_output.results.execution_state == ExecutionState.FAILED


@set_metadata(integration_config=CONFIG, parameters=_PARAMS_SOURCE_TYPE)
def test_add_ip_api_error(
    _script_session: GoogleCloudComputeSession,
    compute_product: GoogleCloudCompute,
    action_output: MockActionOutput,
) -> None:
    """API error → FAILED."""
    set_is_first_run_to_true()
    with compute_product.fail_requests():
        AddIPToFirewallRule.main()

    assert action_output.results.execution_state == ExecutionState.FAILED
