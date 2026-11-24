"""Unit tests for GoogleCloudCompute – Update Firewall Rule action."""
from __future__ import annotations

from TIPCommon.base.action import ExecutionState

from google_cloud_compute.actions import UpdateFirewallRule
from google_cloud_compute.tests.common import (
    CONFIG,
    FIREWALL_RESOURCE_PATH,
    FIREWALL_RULE_NAME,
    MOCK_DATA,

    FAR_FUTURE_DEADLINE_MS,
)
from google_cloud_compute.tests.core.product import GoogleCloudCompute
from google_cloud_compute.tests.core.session import GoogleCloudComputeSession
from integration_testing.common import set_is_first_run_to_true, set_is_first_run_to_false
from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata

_PARAMS_BY_RESOURCE: dict[str, object] = {
    "Resource Name": FIREWALL_RESOURCE_PATH,
    "Source IP ranges": "10.1.0.0/16",
}

_PARAMS_BY_RULE_NAME: dict[str, object] = {
    "Firewall Rule": FIREWALL_RULE_NAME,
    "Source IP ranges": "10.2.0.0/16",
}

_PARAMS_NO_FIELDS_TO_UPDATE: dict[str, object] = {
    "Firewall Rule": FIREWALL_RULE_NAME,
    # No update fields at all → validation error
}

_PARAMS_MISSING_RESOURCE: dict[str, object] = {
    "Source IP ranges": "10.0.0.0/8",
}


@set_metadata(integration_config=CONFIG, parameters=_PARAMS_BY_RESOURCE,
    input_context={"execution_deadline_unix_time_ms": FAR_FUTURE_DEADLINE_MS})
def test_update_firewall_rule_first_run_success(
    _script_session: GoogleCloudComputeSession,
    compute_product: GoogleCloudCompute,
    action_output: MockActionOutput,
) -> None:
    """First run with source IP update → patch operation DONE → COMPLETED."""
    set_is_first_run_to_true()
    compute_product.set_firewall_rule(MOCK_DATA["firewall_rule"])
    compute_product.set_operation(MOCK_DATA["operation_done"])

    UpdateFirewallRule.main()

    assert action_output.results.execution_state == ExecutionState.COMPLETED
    assert action_output.results.result_value is True
    assert "Successfully updated firewall rule" in action_output.results.output_message


@set_metadata(integration_config=CONFIG, parameters=_PARAMS_BY_RULE_NAME,
    input_context={"execution_deadline_unix_time_ms": FAR_FUTURE_DEADLINE_MS})
def test_update_firewall_rule_by_name_success(
    _script_session: GoogleCloudComputeSession,
    compute_product: GoogleCloudCompute,
    action_output: MockActionOutput,
) -> None:
    """Update by firewall rule name → COMPLETED, True."""
    set_is_first_run_to_true()
    compute_product.set_firewall_rule(MOCK_DATA["firewall_rule"])
    compute_product.set_operation(MOCK_DATA["operation_done"])

    UpdateFirewallRule.main()

    assert action_output.results.execution_state == ExecutionState.COMPLETED
    assert action_output.results.result_value is True


@set_metadata(integration_config=CONFIG, parameters=_PARAMS_BY_RESOURCE,
    input_context={"execution_deadline_unix_time_ms": FAR_FUTURE_DEADLINE_MS})
def test_update_firewall_rule_operation_running(
    _script_session: GoogleCloudComputeSession,
    compute_product: GoogleCloudCompute,
    action_output: MockActionOutput,
) -> None:
    """Operation RUNNING → IN_PROGRESS."""
    set_is_first_run_to_true()
    compute_product.set_firewall_rule(MOCK_DATA["firewall_rule"])
    compute_product.set_operation(MOCK_DATA["operation_running"])

    UpdateFirewallRule.main()

    assert action_output.results.execution_state == ExecutionState.IN_PROGRESS


@set_metadata(integration_config=CONFIG, parameters=_PARAMS_NO_FIELDS_TO_UPDATE)
def test_update_firewall_rule_no_update_fields(
    _script_session: GoogleCloudComputeSession,
    _compute_product: GoogleCloudCompute,
    action_output: MockActionOutput,
) -> None:
    """No update fields provided → FAILED (validation error)."""
    set_is_first_run_to_true()

    UpdateFirewallRule.main()

    assert action_output.results.execution_state == ExecutionState.FAILED


@set_metadata(integration_config=CONFIG, parameters=_PARAMS_MISSING_RESOURCE)
def test_update_firewall_rule_missing_resource(
    _script_session: GoogleCloudComputeSession,
    _compute_product: GoogleCloudCompute,
    action_output: MockActionOutput,
) -> None:
    """No resource or firewall rule name → FAILED."""
    set_is_first_run_to_true()

    UpdateFirewallRule.main()

    assert action_output.results.execution_state == ExecutionState.FAILED


@set_metadata(integration_config=CONFIG, parameters=_PARAMS_BY_RESOURCE)
def test_update_firewall_rule_api_error(
    _script_session: GoogleCloudComputeSession,
    compute_product: GoogleCloudCompute,
    action_output: MockActionOutput,
) -> None:
    """API error → FAILED."""
    set_is_first_run_to_true()
    with compute_product.fail_requests():
        UpdateFirewallRule.main()

    assert action_output.results.execution_state == ExecutionState.FAILED
