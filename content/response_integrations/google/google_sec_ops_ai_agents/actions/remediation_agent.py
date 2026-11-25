"""Remediation Agent action script."""
from __future__ import annotations

from __future__ import annotations

import dataclasses

from typing import TYPE_CHECKING, Any
from google_sec_ops_ai_agents.core import consts
from google_sec_ops_ai_agents.core.base_action import BaseAction
from google_sec_ops_ai_agents.core.data_models import (
    RemediationPlanExecutionState,
    RemediationPlanState,
)
from dataclass_wizard import JSONWizard
from google_sec_ops_ai_agents.core.exceptions import TriageError
from google_sec_ops_ai_agents.core.remediation_manager import RemediationManager
from TIPCommon.base.action import ExecutionState
from TIPCommon.extraction import extract_action_param

if TYPE_CHECKING:
    from typing import NoReturn

SCRIPT_NAME: str = "Remediation Agent"
CONTEXT_KEY_REMEDIATION_JOB_ID: str = "chronicle_remediation_job_id"
ALERT_NOT_FROM_SIEM_MESSAGE: str = (
    "Remediation agent cannot execute on this alert as it lacks a valid SIEM Alert ID."
)
MISSING_JOB_ID_IN_CONTEXT_ERROR: str = (
    "Could not find remediation job ID in execution context."
)
FAILED_TO_OBTAIN_JOB_ID_ERROR: str = "Failed to obtain remediation job ID."


@dataclasses.dataclass(slots=True, frozen=True)
class RemediationExecutionContext(JSONWizard):
    """Data model holding contextual state passed between async action execution cycles."""

    plan_id: str = ""

    @classmethod
    def read_context(cls, soar_action: Any) -> RemediationExecutionContext:
        """Read contextual data from action execution inputs and alert context properties.

        Args:
            soar_action: The SiemplifyAction execution context.

        Returns:
            RemediationExecutionContext: Dataclass containing execution context values.
        """
        raw_additional_data = extract_action_param(
            soar_action,
            param_name="additional_data",
            is_mandatory=False,
            default_value="{}",
            print_value=False,
        )
        context: RemediationExecutionContext | None = None
        if raw_additional_data:
            try:
                context = cls.from_json(raw_additional_data)
            except Exception:
                context = None

        plan_id = context.plan_id if context else ""
        if not plan_id:
            plan_id = (
                soar_action.get_alert_context_property(CONTEXT_KEY_REMEDIATION_JOB_ID)
                or ""
            )

        return cls(plan_id=plan_id)

    def persist_context(self, soar_action: Any) -> str:
        """Persist contextual data across execution cycles and alert context properties.

        Args:
            soar_action: The SiemplifyAction execution context.

        Returns:
            str: JSON string representation of context data.
        """
        if self.plan_id:
            soar_action.set_alert_context_property(
                CONTEXT_KEY_REMEDIATION_JOB_ID, self.plan_id
            )
        return self.to_json()


class RemediationAgent(BaseAction):
    """Remediation Agent action handler.

    Initializes state indicators and handles async execution flow for remediation plans.
    """

    def __init__(self) -> None:
        """Initialize RemediationAgent action."""
        super().__init__(f"{consts.INTEGRATION_NAME} - {SCRIPT_NAME}")

        self.remediation_manager: RemediationManager | None = None

    def _get_siem_alert_id(self) -> str | None:
        """Extract the SIEM alert ID from the current alert context."""
        current_alert = self.soar_action.current_alert
        props = getattr(current_alert, "additional_properties", None) or {}
        return props.get("SiemAlertId") or props.get("SystemAlertId")

    def _perform_action(self, _: None = None) -> None:
        """Perform action entrypoint.

        Args:
            _: Unused positional parameter.
        """
        alert_id = self._get_siem_alert_id()
        if not alert_id:
            self.logger.info(
                f"[STEP 1: VALIDATION FAILED] {ALERT_NOT_FROM_SIEM_MESSAGE}"
            )
            self.output_message = ALERT_NOT_FROM_SIEM_MESSAGE
            self.execution_state = ExecutionState.FAILED
            self.result_value = False
            return

        self.remediation_manager = RemediationManager(
            api_client=self.api_client,
            logger=self.logger,
        )
        self._run_remediation_state_machine(
            is_first_run=self.is_first_run, alert_id=alert_id
        )

    def _run_remediation_state_machine(self, is_first_run: bool, alert_id: str) -> None:
        """State machine orchestrating Intake, Plan Gen, Analyst Review, Action Exec, and Summary.

        Args:
            is_first_run: Whether this is the initial execution cycle.
            alert_id: SIEM alert identifier.
        """
        self.logger.info(f"[STATE MACHINE START] is_first_run={is_first_run}, Alert ID={alert_id}")

        if is_first_run:
            self.logger.info(f"[INTAKE PHASE] Checking existing plans for Alert ID: {alert_id}")

            existing_plans = self.remediation_manager.list_remediation_plans(alert_id=alert_id)
            latest_plan = existing_plans.remediation_plans[0] if existing_plans.remediation_plans else None
            if latest_plan:
                self.logger.info(
                    f"[INTAKE PHASE] Found existing plan: {latest_plan.name} "
                    f"(State: {latest_plan.state.value})"
                )

                if latest_plan.state in {
                    RemediationPlanState.INITIALIZED,
                    RemediationPlanState.REQUESTED,
                    RemediationPlanState.SUGGESTED,
                    RemediationPlanState.APPROVED,
                }:
                    self.logger.info(
                        f"[INTAKE PHASE: BRANCH A] Attaching to active plan: {latest_plan.name}"
                    )
                    context = RemediationExecutionContext(plan_id=latest_plan.plan_id)
                    self.result_value = context.persist_context(self.soar_action)
                    # Proceed immediately to Phase 2 (Polling)
                    self._evaluate_polling_state(context=context)
                    return

            # Branch B: No Active Plan Found or Latest Plan is not in active state (e.g. ERROR, terminal)
            self.logger.info(f"[INTAKE PHASE: BRANCH B] Requesting new plan for Alert ID: {alert_id}")

            remediation_plan = self.remediation_manager.generate_remediation_plan(alert_id)

            self.output_message = f"Successfully triggered remediation job: {remediation_plan.plan_id}"
            self.execution_state = ExecutionState.IN_PROGRESS

            context = RemediationExecutionContext(plan_id=remediation_plan.plan_id)
            self.result_value = context.persist_context(self.soar_action)
            return

        context = RemediationExecutionContext.read_context(self.soar_action)
        self._evaluate_polling_state(context=context)

    def _evaluate_polling_state(self, context: RemediationExecutionContext) -> None:
        """Helper to evaluate current plan status, actions progress, and summary.

        Args:
            context: Execution context model instance.
        """
        plan_id = context.plan_id
        if not plan_id:
            raise TriageError(MISSING_JOB_ID_IN_CONTEXT_ERROR)

        plan_details = self.remediation_manager.get_remediation_plan_details(plan_id)
        plan_state_val = plan_details.state.value

        # Phase 2.1: Plan generation in progress
        if plan_details.state in {
            RemediationPlanState.INITIALIZED,
            RemediationPlanState.REQUESTED,
        }:
            self.logger.info(
                f"[POLLING STATE: PLAN GENERATING] Plan {plan_id} generation in progress (State: {plan_state_val})."
            )
            self.output_message = (
                f"Remediation job {plan_id} is still running (Status: {plan_details.state.display_name})"
            )
            self.execution_state = ExecutionState.IN_PROGRESS
            self.result_value = context.persist_context(self.soar_action)
            return

        # Phase 2.1: Plan generation failed or was declined
        if plan_details.state in {
            RemediationPlanState.ERROR,
            RemediationPlanState.DECLINED,
        }:
            err_msg = (
                str(plan_details.status_details)
                if plan_details.status_details
                else f"Plan ended with status: {plan_details.state.display_name}"
            )
            self.logger.info(
                f"[POLLING STATE: PLAN FAILED] Plan {plan_id} (State: {plan_state_val}): {err_msg}"
            )
            self.output_message = (
                f"Remediation plan generation failed or was declined: {err_msg}"
            )
            self.execution_state = ExecutionState.FAILED
            self.result_value = False
            self.json_results = {
                "agent_raw_data": plan_details.to_dict(),
                "action_executions": [],
                "status": plan_state_val,
            }
            return

        # Phase 2.2: Plan is SUGGESTED or APPROVED -> inspect latest_execution
        if plan_details.state in {
            RemediationPlanState.SUGGESTED,
            RemediationPlanState.APPROVED,
        }:
            latest_execution = plan_details.latest_execution
            if not latest_execution:
                self.logger.info(
                    f"[POLLING STATE: AWAITING APPROVAL] Plan {plan_id} awaits analyst approval or execution trigger (State: {plan_state_val})."
                )
                self.output_message = (
                    f"Remediation job {plan_id} awaits analyst approval or execution trigger."
                )
                self.execution_state = ExecutionState.IN_PROGRESS
                self.result_value = context.persist_context(self.soar_action)
                return

            # latest_execution is present -> evaluate execution state
            exec_state_val = latest_execution.state.value
            if latest_execution.state == RemediationPlanExecutionState.IN_PROGRESS:
                self.logger.info(
                    f"[POLLING STATE: IN_PROGRESS] Plan {plan_id} execution in progress."
                )
                self.output_message = (
                    f"Remediation job {plan_id} is still running (Status: {latest_execution.state.display_name})"
                )
                self.execution_state = ExecutionState.IN_PROGRESS
                self.result_value = context.persist_context(self.soar_action)
                return

            action_executions = self.remediation_manager.list_remediation_action_executions(plan_id)
            action_exec_list = [
                execution.to_dict()
                for execution in action_executions.remediation_action_executions
            ]

            if latest_execution.state == RemediationPlanExecutionState.EXECUTED:
                self.logger.info(
                    f"[POLLING STATE: COMPLETED] Plan {plan_id} completed successfully."
                )
                self.output_message = (
                    f"Remediation job successfully ended with status: {latest_execution.state.display_name}"
                )
                self.result_value = True
                self.execution_state = ExecutionState.COMPLETED
                self.json_results = {
                    "agent_raw_data": plan_details.to_dict(),
                    "action_executions": action_exec_list,
                    "status": exec_state_val,
                }
                return

            # Execution ended with non-success status (REJECTED, ERROR, etc.)
            self.logger.info(
                f"[POLLING STATE: FAILED] Plan {plan_id} execution ended with status {exec_state_val}."
            )
            self.output_message = (
                f"Remediation job ended with non-success status: {latest_execution.state.display_name}"
            )
            self.execution_state = ExecutionState.FAILED
            self.result_value = False
            self.json_results = {
                "agent_raw_data": plan_details.to_dict(),
                "action_executions": action_exec_list,
                "status": exec_state_val,
            }
            return

        # Fallback for unexpected plan states (e.g. RemediationPlanState.UNSPECIFIED)
        self.logger.info(
            f"[POLLING STATE: FAILED] Plan {plan_id} ended with unexpected status: {plan_state_val}."
        )
        self.output_message = (
            f"Remediation job ended with unexpected status: {plan_details.state.display_name}"
        )
        self.execution_state = ExecutionState.FAILED
        self.result_value = False
        self.json_results = {
            "agent_raw_data": plan_details.to_dict(),
            "action_executions": [],
            "status": plan_state_val,
        }


def main() -> NoReturn:
    """Execute the main action runner entrypoint."""
    RemediationAgent().run()


if __name__ == "__main__":
    main()
