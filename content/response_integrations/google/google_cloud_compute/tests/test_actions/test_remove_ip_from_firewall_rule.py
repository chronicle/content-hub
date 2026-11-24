"""Unit tests for GoogleCloudCompute – Remove IP From Firewall Rule action."""
from __future__ import annotations

from TIPCommon.base.action import ExecutionState

from google_cloud_compute.actions import RemoveIPFromFirewallRule
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

_PARAMS_REMOVE_SOURCE: dict[str, object] = {
    "Resource Name": FIREWALL_RESOURCE_PATH,
    "IP Ranges": "10.0.0.0/8",  # matches canned firewall_rule sourceRanges
    "Type": "SOURCE",
}

_PARAMS_REMOVE_DESTINATION: dict[str, object] = {
    "Resource Name": FIREWALL_RESOURCE_PATH,
    "IP Ranges": "192.168.0.0/16",
    "Type": "DESTINATION",
}

_PARAMS_REMOVE_NON_EXISTING_IP: dict[str, object] = {
    "Resource Name": FIREWALL_RESOURCE_PATH,
    "IP Ranges": "99.99.99.99/32",
    "Type": "SOURCE",
}

_PARAMS_MISSING_RESOURCE: dict[str, object] = {
    "IP Ranges": "10.0.0.0/8",
    "Type": "SOURCE",
}


@set_metadata(integration_config=CONFIG, parameters=_PARAMS_REMOVE_SOURCE,
    input_context={"execution_deadline_unix_time_ms": FAR_FUTURE_DEADLINE_MS})
def test_remove_ip_source_success(
    _script_session: GoogleCloudComputeSession,
    compute_product: GoogleCloudCompute,
    action_output: MockActionOutput,
) -> None:
    """Removing an existing source IP on first run → COMPLETED, True."""
    set_is_first_run_to_true()
    compute_product.set_firewall_rule(MOCK_DATA["firewall_rule"])
    compute_product.set_operation(MOCK_DATA["operation_done"])

    RemoveIPFromFirewallRule.main()

    assert action_output.results.execution_state == ExecutionState.COMPLETED
    assert action_output.results.result_value is True
    assert "Successfully updated firewall rule" in action_output.results.output_message


@set_metadata(integration_config=CONFIG, parameters=_PARAMS_REMOVE_NON_EXISTING_IP,
    input_context={"execution_deadline_unix_time_ms": FAR_FUTURE_DEADLINE_MS})
def test_remove_ip_non_existing_still_succeeds(
    _script_session: GoogleCloudComputeSession,
    compute_product: GoogleCloudCompute,
    action_output: MockActionOutput,
) -> None:
    """Removing an IP that is not in the range list is a no-op → COMPLETED.

    ISSUE FINDER: ``remove_ip_ranges`` uses set.difference_update, which silently
    produces the original set unchanged when the IP to remove is absent. The
    action then issues a PATCH with sourceRanges=["none"] placeholder if the
    resulting set is empty, which could inadvertently lock down the firewall rule.
    """
    set_is_first_run_to_true()
    compute_product.set_firewall_rule(MOCK_DATA["firewall_rule"])
    compute_product.set_operation(MOCK_DATA["operation_done"])

    RemoveIPFromFirewallRule.main()

    assert action_output.results.execution_state == ExecutionState.COMPLETED


@set_metadata(integration_config=CONFIG, parameters=_PARAMS_REMOVE_SOURCE,
    input_context={"execution_deadline_unix_time_ms": FAR_FUTURE_DEADLINE_MS})
def test_remove_ip_operation_running(
    _script_session: GoogleCloudComputeSession,
    compute_product: GoogleCloudCompute,
    action_output: MockActionOutput,
) -> None:
    """Operation RUNNING on first-run → IN_PROGRESS."""
    set_is_first_run_to_true()
    compute_product.set_firewall_rule(MOCK_DATA["firewall_rule"])
    compute_product.set_operation(MOCK_DATA["operation_running"])

    RemoveIPFromFirewallRule.main()

    assert action_output.results.execution_state == ExecutionState.IN_PROGRESS


@set_metadata(integration_config=CONFIG, parameters=_PARAMS_MISSING_RESOURCE)
def test_remove_ip_missing_resource(
    _script_session: GoogleCloudComputeSession,
    _compute_product: GoogleCloudCompute,
    action_output: MockActionOutput,
) -> None:
    """Missing both resource name and firewall rule → FAILED."""
    set_is_first_run_to_true()

    RemoveIPFromFirewallRule.main()

    assert action_output.results.execution_state == ExecutionState.FAILED


@set_metadata(integration_config=CONFIG, parameters=_PARAMS_REMOVE_SOURCE)
def test_remove_ip_api_error(
    _script_session: GoogleCloudComputeSession,
    compute_product: GoogleCloudCompute,
    action_output: MockActionOutput,
) -> None:
    """API error → FAILED."""
    set_is_first_run_to_true()
    with compute_product.fail_requests():
        RemoveIPFromFirewallRule.main()

    assert action_output.results.execution_state == ExecutionState.FAILED
