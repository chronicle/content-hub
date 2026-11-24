from __future__ import annotations

import json

from TIPCommon.base.action.data_models import ExecutionState
from TIPCommon.extraction import extract_action_param
from TIPCommon.validation import ParameterValidator

from google_cloud_compute.core.GoogleCloudComputeConstants import (
    INTEGRATION_NAME,
    EXECUTE_VM_PATCH_JOB_SCRIPT_NAME,
)
from google_cloud_compute.core.GoogleCloudComputeDatamodels import (
    RolloutStrategy,
    PatchJob,
)
from google_cloud_compute.core.GoogleCloudComputeExceptions import(
    GoogleCloudComputeOperationError,
    GoogleCloudComputeTimeoutError,
)
from google_cloud_compute.core.GoogleCloudComputeGenerics import BaseGoogleCloudComputeAsyncAction
from google_cloud_compute.core.GoogleCloudComputeManager import GoogleCloudComputeManager
from google_cloud_compute.core.GoogleCloudComputeUtils import is_async_action_global_timeout_approaching


class ExecuteVMPatchJob(BaseGoogleCloudComputeAsyncAction):
    def __init__(self, script_name: str) -> None:
        super().__init__(script_name)
        self.result_value = self._result_value = False
        self.output_message = ""
        self.json_results = {}
        self.execution_state = ExecutionState.COMPLETED

    def _extract_action_params(self) -> None:
        self.params.instance_filter_object = extract_action_param(
            self.soar_action,
            is_mandatory=True,
            param_name="Instance Filter Object",
            print_value=True,
        )
        self.params.name = extract_action_param(
            self.soar_action,
            is_mandatory=True,
            param_name="Name",
            print_value=True,
        )
        self.params.description = extract_action_param(
            self.soar_action, param_name="Description"
        )
        self.params.patching_config_object = extract_action_param(
            self.soar_action, param_name="Patching Config Object", print_value=True
        )
        self.params.patch_duration_timeout = extract_action_param(
            self.soar_action,
            is_mandatory=True,
            param_name="Patch Duration Timeout",
            print_value=True,
        )
        self.params.rollout_strategy = extract_action_param(
            self.soar_action, param_name="Rollout Strategy", print_value=True
        )
        self.params.disruption_budget = extract_action_param(
            self.soar_action,
            is_mandatory=True,
            param_name="Disruption Budget",
            print_value=True,
        )
        self.params.wait_for_completion = extract_action_param(
            self.soar_action,
            input_type=bool,
            param_name="Wait For Completion",
            print_value=True,
        )
        self.params.fail_if_completed_with_errors = extract_action_param(
            self.soar_action,
            input_type=bool,
            param_name="Fail If Completed With Errors",
            print_value=True
        )

    def _validate_params(self) -> None:
        super()._validate_params()
        validator = ParameterValidator(self.soar_action)

        self.params.instance_filter_object = validator.validate_json(
            json_string=self.params.instance_filter_object,
            param_name="Instance Filter Object"
        )
        if self.params.patching_config_object:
            self.params.patching_config_object = validator.validate_json(
                json_string=self.params.patching_config_object,
                param_name="Patching Config Object"
            )
        self.params.patch_duration_timeout = validator.validate_positive(
            value=self.params.patch_duration_timeout,
            param_name="Patch Duration Timeout",
        )
        self.params.rollout_strategy_enum = RolloutStrategy(
            validator.validate_ddl(
                value=self.params.rollout_strategy,
                param_name="Rollout Strategy",
                ddl_values=[rs.value for rs in RolloutStrategy]
            )
        )
        validator.validate_positive(
            value=(
                self.params.disruption_budget[:-1]
                if self.params.disruption_budget.endswith("%") else
                self.params.disruption_budget
            ),
            param_name="Disruption Budget"
        )

    def _start_patch_job(self, manager: GoogleCloudComputeManager) -> PatchJob:
        """Start Patch Job operation."""
        patch_job = PatchJob(
            description=self.params.description,
            display_name=self.params.name,
            duration=f"{(self.params.patch_duration_timeout * 60)}s",
            instance_filter=self.params.instance_filter_object,
            patch_config=self.params.patching_config_object,
            rollout={
                "mode": self.params.rollout_strategy_enum.name,
                "disruptionBudget": (
                    {"percent": int(self.params.disruption_budget[:-1])}
                    if self.params.disruption_budget.endswith("%")
                    else {"fixed": int(self.params.disruption_budget)}
                )
            }
        )
        return manager.execute_patch_job(patch_job)

    def _set_success(self) -> None:
        """Set success state."""
        self.result_value = True
        self.output_message = (
            f"Successfully executed VM patching job in {INTEGRATION_NAME}"
        )

    def _set_success_and_completed(self) -> None:
        """Set success state."""
        self.result_value = True
        self.output_message = (
            f"Successfully executed and completed VM patching job in {INTEGRATION_NAME}"
        )

    def _set_cancelled(self) -> None:
        """Set cancelled state."""
        self.output_message = (
            f"The executed patching job was canceled in {INTEGRATION_NAME}."
        )

    def _set_failed(self, patch_job: PatchJob) -> None:
        """Set failed state."""
        if self.params.fail_if_completed_with_errors:
            raise GoogleCloudComputeOperationError(
                "the executed patching job was completed, but with errors in "
                f"{INTEGRATION_NAME}. Errors: {patch_job.error_message}."
            )

        self.output_message = (
            "The executed patching job was completed, but with errors in "
            f"{INTEGRATION_NAME}. Errors: {patch_job.error_message}."
        )

    def _set_timed_out(self) -> None:
        """Set timed out state."""
        raise GoogleCloudComputeTimeoutError(
            "patching job ran into a timeout during execution. Please adjust the "
            "patching job configuration and try again."
        )

    def _perform_action(self, _=None) -> None:
        manager = self._api_client
        if is_async_action_global_timeout_approaching(
                siemplify=self.soar_action, start_time=self.action_start_time
        ):
            raise GoogleCloudComputeTimeoutError(
                "action ran into a timeout during execution. Please increase "
                "the timeout in IDE."
            )

        if self.is_first_run:
            patch_job = self._start_patch_job(manager)

        else:
            patch_job_name = self.params.async_context
            patch_job = manager.get_patch_job(patch_job_name)

        self.json_results = patch_job.raw_data
        if not self.params.wait_for_completion:
            self._set_success()
            return

        if patch_job.is_finished:
            self._set_success_and_completed()
            return

        if patch_job.is_cancelled:
            self._set_cancelled()
            return

        if patch_job.is_failed:
            self._set_failed(patch_job)
            return

        if patch_job.is_timed_out:
            self._set_timed_out()

        self._result_value = json.dumps(patch_job.name)
        self.execution_state = ExecutionState.IN_PROGRESS
        self.output_message = patch_job.state.value


def main() -> None:
    ExecuteVMPatchJob(
        f"{INTEGRATION_NAME} - {EXECUTE_VM_PATCH_JOB_SCRIPT_NAME}"
    ).run()


if __name__ == "__main__":
    main()
