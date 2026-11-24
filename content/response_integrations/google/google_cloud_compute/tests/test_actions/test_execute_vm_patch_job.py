"""Unit tests for GoogleCloudCompute – Execute VM Patch Job action."""
from __future__ import annotations

from TIPCommon.base.action import ExecutionState

from google_cloud_compute.actions import ExecuteVMPatchJob
from google_cloud_compute.tests.common import (
    CONFIG,
    MOCK_DATA,
    PATCH_JOB_DISRUPTION_BUDGET,
    PATCH_JOB_DURATION,
    PATCH_JOB_INSTANCE_FILTER,
    PATCH_JOB_ROLLOUT_STRATEGY,

    FAR_FUTURE_DEADLINE_MS,
)
from google_cloud_compute.tests.core.product import GoogleCloudCompute
from google_cloud_compute.tests.core.session import GoogleCloudComputeSession
from integration_testing.common import set_is_first_run_to_true, set_is_first_run_to_false
from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata

_BASE_PARAMS: dict[str, object] = {
    "Instance Filter Object": PATCH_JOB_INSTANCE_FILTER,
    "Name": "Test Patch Job",
    "Description": "Automated patch test",
    "Patch Duration Timeout": str(PATCH_JOB_DURATION),
    "Rollout Strategy": PATCH_JOB_ROLLOUT_STRATEGY,
    "Disruption Budget": PATCH_JOB_DISRUPTION_BUDGET,
    "Wait For Completion": "False",
    "Fail If Completed With Errors": "False",
}

_PARAMS_WAIT_FOR_COMPLETION: dict[str, object] = {
    **_BASE_PARAMS,
    "Wait For Completion": "True",
}

_PARAMS_FAIL_ON_ERRORS: dict[str, object] = {
    **_BASE_PARAMS,
    "Wait For Completion": "True",
    "Fail If Completed With Errors": "True",
}

_PARAMS_FIXED_BUDGET: dict[str, object] = {
    **_BASE_PARAMS,
    "Disruption Budget": "5",  # fixed count, not percentage
}

_PARAMS_WAIT_FOR_COMPLETION_SUBSEQUENT: dict[str, object] = {
    **_PARAMS_WAIT_FOR_COMPLETION,
    "additional_data": '"projects/test-project/patchJobs/patch-job-uuid-1234"',
}

_PARAMS_FAIL_ON_ERRORS_SUBSEQUENT: dict[str, object] = {
    **_PARAMS_FAIL_ON_ERRORS,
    "additional_data": '"projects/test-project/patchJobs/patch-job-uuid-1234"',
}

_PARAMS_MISSING_MANDATORY: dict[str, object] = {
    # Missing Instance Filter Object, Name, Patch Duration Timeout, Disruption Budget
    "Rollout Strategy": PATCH_JOB_ROLLOUT_STRATEGY,
    "Wait For Completion": "False",
    "Fail If Completed With Errors": "False",
}


@set_metadata(integration_config=CONFIG, parameters=_BASE_PARAMS,
    input_context={"execution_deadline_unix_time_ms": FAR_FUTURE_DEADLINE_MS})
def test_execute_patch_job_no_wait_success(
    _script_session: GoogleCloudComputeSession,
    compute_product: GoogleCloudCompute,
    action_output: MockActionOutput,
) -> None:
    """First run, Wait For Completion=False → job launched → COMPLETED, True."""
    set_is_first_run_to_true()
    compute_product.set_patch_job(MOCK_DATA["patch_job_started"])

    ExecuteVMPatchJob.main()

    assert action_output.results.execution_state == ExecutionState.COMPLETED
    assert action_output.results.result_value is True
    assert "Successfully executed VM patching job" in action_output.results.output_message


@set_metadata(integration_config=CONFIG, parameters=_PARAMS_WAIT_FOR_COMPLETION,
    input_context={"execution_deadline_unix_time_ms": FAR_FUTURE_DEADLINE_MS})
def test_execute_patch_job_wait_job_still_running(
    _script_session: GoogleCloudComputeSession,
    compute_product: GoogleCloudCompute,
    action_output: MockActionOutput,
) -> None:
    """Wait=True, job still STARTED on first run → IN_PROGRESS."""
    set_is_first_run_to_true()
    compute_product.set_patch_job(MOCK_DATA["patch_job_started"])

    ExecuteVMPatchJob.main()

    assert action_output.results.execution_state == ExecutionState.IN_PROGRESS


@set_metadata(integration_config=CONFIG, parameters=_PARAMS_WAIT_FOR_COMPLETION_SUBSEQUENT,
    input_context={"execution_deadline_unix_time_ms": FAR_FUTURE_DEADLINE_MS})
def test_execute_patch_job_wait_job_succeeded(
    _script_session: GoogleCloudComputeSession,
    compute_product: GoogleCloudCompute,
    action_output: MockActionOutput,
) -> None:
    """Wait=True, job SUCCEEDED on subsequent run → COMPLETED, True."""
    set_is_first_run_to_false()
    compute_product.set_patch_job(MOCK_DATA["patch_job_succeeded"])

    ExecuteVMPatchJob.main()

    assert action_output.results.execution_state == ExecutionState.COMPLETED
    assert action_output.results.result_value is True
    assert "completed" in action_output.results.output_message.lower()


@set_metadata(integration_config=CONFIG, parameters=_PARAMS_FAIL_ON_ERRORS)
def test_execute_patch_job_completed_with_errors_fail(
    _script_session: GoogleCloudComputeSession,
    compute_product: GoogleCloudCompute,
    action_output: MockActionOutput,
) -> None:
    """Wait=True, Fail If Errors=True, job COMPLETED_WITH_ERRORS → FAILED.

    ISSUE FINDER: ``_set_failed`` raises ``GoogleCloudComputeOperationError``,
    which propagates up and is caught by the Action base class as a generic
    exception, resulting in EXECUTION_STATE_FAILED.  If the operator sets
    Fail If Completed With Errors=False the same state yields COMPLETED with
    a warning message instead.  This asymmetry is documented but not tested
    in the action's existing tests.
    """
    set_is_first_run_to_false()
    compute_product.set_patch_job(MOCK_DATA["patch_job_with_errors"])

    ExecuteVMPatchJob.main()

    assert action_output.results.execution_state == ExecutionState.FAILED
    assert action_output.results.result_value is False


@set_metadata(integration_config=CONFIG, parameters=_PARAMS_WAIT_FOR_COMPLETION_SUBSEQUENT,
    input_context={"execution_deadline_unix_time_ms": FAR_FUTURE_DEADLINE_MS})
def test_execute_patch_job_completed_with_errors_no_fail(
    _script_session: GoogleCloudComputeSession,
    compute_product: GoogleCloudCompute,
    action_output: MockActionOutput,
) -> None:
    """Fail If Errors=False, COMPLETED_WITH_ERRORS → COMPLETED with warning message."""
    set_is_first_run_to_false()
    compute_product.set_patch_job(MOCK_DATA["patch_job_with_errors"])

    ExecuteVMPatchJob.main()

    assert action_output.results.execution_state == ExecutionState.COMPLETED
    assert "errors" in action_output.results.output_message.lower()


@set_metadata(integration_config=CONFIG, parameters=_PARAMS_FIXED_BUDGET,
    input_context={"execution_deadline_unix_time_ms": FAR_FUTURE_DEADLINE_MS})
def test_execute_patch_job_fixed_disruption_budget(
    _script_session: GoogleCloudComputeSession,
    compute_product: GoogleCloudCompute,
    action_output: MockActionOutput,
) -> None:
    """Fixed disruption budget (integer, no '%' suffix) is accepted → COMPLETED."""
    set_is_first_run_to_true()
    compute_product.set_patch_job(MOCK_DATA["patch_job_started"])

    ExecuteVMPatchJob.main()

    assert action_output.results.execution_state == ExecutionState.COMPLETED
    assert action_output.results.result_value is True


@set_metadata(integration_config=CONFIG, parameters=_BASE_PARAMS)
def test_execute_patch_job_api_error(
    _script_session: GoogleCloudComputeSession,
    compute_product: GoogleCloudCompute,
    action_output: MockActionOutput,
) -> None:
    """API error on execute_patch_job → FAILED."""
    set_is_first_run_to_true()
    with compute_product.fail_requests():
        ExecuteVMPatchJob.main()

    assert action_output.results.execution_state == ExecutionState.FAILED
    assert action_output.results.result_value is False
