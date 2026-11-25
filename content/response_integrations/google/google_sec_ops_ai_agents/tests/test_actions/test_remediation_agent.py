from __future__ import annotations

import json
from unittest.mock import MagicMock, PropertyMock, patch

from google_sec_ops_ai_agents.actions import remediation_agent
from google_sec_ops_ai_agents.actions.remediation_agent import (
    ALERT_NOT_FROM_SIEM_MESSAGE,
    CONTEXT_KEY_REMEDIATION_JOB_ID,
)
from soar_sdk.SiemplifyAction import SiemplifyAction
from google_sec_ops_ai_agents.tests import common
from google_sec_ops_ai_agents.tests.core.product import (
    GoogleSecOpsAiAgents,
)
from google_sec_ops_ai_agents.tests.core.session import (
    GoogleSecOpsAiAgentsSession,
)
from integration_testing.common import set_is_first_run_to_true, set_is_first_run_to_false
from integration_testing.platform.external_context import (
    ExternalContextRow,
    MockExternalContext,
)
from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata
from TIPCommon.base.action import ExecutionState
from TIPCommon.data_models import DatabaseContextType


ALERT_ID = "alert-123"
PLAN_DATA = common.MOCK_DATA["remediation_plans"]
EXEC_DATA = common.MOCK_DATA["remediation_action_executions"]
PLAN_ID: int = int(
    PLAN_DATA["generated_plan"].get("id")
    or PLAN_DATA["generated_plan"]["name"].split("/")[-1]
)
PLAN_NAME = PLAN_ID

JOB_CONTEXT: list[ExternalContextRow[str]] = [
    ExternalContextRow(
        context_type=DatabaseContextType.ALERT,
        identifier="Phishing email detector3wM/eL7XV3hdthDGI3TUCzTZrm+gwID5DaLrxaRCT6U=_c8f65349-8519-4d4b-8aca-3e0075e61003",
        property_key=CONTEXT_KEY_REMEDIATION_JOB_ID,
        property_value=str(PLAN_ID),
    )
]


@set_metadata(
    integration_config=common.CONFIG,
)
def test_remediation_agent_first_run_triggers_new_plan(
    google_chronicle_ai_agents: GoogleSecOpsAiAgents,
    script_session: GoogleSecOpsAiAgentsSession,
    action_output: MockActionOutput,
) -> None:
    """Test first run with no existing plan triggers new generation (Branch B)."""
    google_chronicle_ai_agents.cleanup_remediation()
    google_chronicle_ai_agents.add_remediation_plans(ALERT_ID, [])
    google_chronicle_ai_agents.add_generated_remediation_plan(
        ALERT_ID, PLAN_DATA["generated_plan"]
    )
    set_is_first_run_to_true()

    remediation_agent.main()

    assert action_output.results.execution_state == ExecutionState.IN_PROGRESS
    assert action_output.results.output_message == (
        f"Successfully triggered remediation job: {PLAN_NAME}"
    )
    assert action_output.results.json_output is None
    assert action_output.results.result_value is True


@set_metadata(
    integration_config=common.CONFIG,
)
def test_remediation_agent_first_run_branch_a_active_plan(
    google_chronicle_ai_agents: GoogleSecOpsAiAgents,
    script_session: GoogleSecOpsAiAgentsSession,
    action_output: MockActionOutput,
) -> None:
    """Test first run finds an existing active plan and fast-paths to polling (Branch A)."""
    google_chronicle_ai_agents.cleanup_remediation()
    active_plan = PLAN_DATA["plan_suggested_awaiting_approval"]
    google_chronicle_ai_agents.add_remediation_plans(ALERT_ID, [active_plan])
    google_chronicle_ai_agents.add_remediation_plan_details(PLAN_NAME, active_plan)
    set_is_first_run_to_true()

    remediation_agent.main()

    assert action_output.results.execution_state == ExecutionState.IN_PROGRESS
    assert (
        action_output.results.output_message
        == f"Remediation job {PLAN_NAME} awaits analyst approval or execution trigger."
    )


@set_metadata(
    integration_config=common.CONFIG,
)
def test_remediation_agent_first_run_selects_latest_active_plan(
    google_chronicle_ai_agents: GoogleSecOpsAiAgents,
    script_session: GoogleSecOpsAiAgentsSession,
    action_output: MockActionOutput,
) -> None:
    """Test that when multiple active plans exist, the latest active plan is chosen."""
    google_chronicle_ai_agents.cleanup_remediation()
    older_name = "projects/secops-prod/locations/us-central1/instances/siem-instance-1/remediationPlans/101"
    newer_name = "projects/secops-prod/locations/us-central1/instances/siem-instance-1/remediationPlans/102"

    older_plan = dict(PLAN_DATA["plan_suggested_awaiting_approval"])
    older_plan["name"] = older_name
    older_plan["createTime"] = "2026-09-01T10:00:00Z"

    newer_plan = dict(PLAN_DATA["plan_suggested_awaiting_approval"])
    newer_plan["name"] = newer_name
    newer_plan["createTime"] = "2026-09-07T12:00:00Z"

    # The API returns plans with the latest plan first (index 0)
    google_chronicle_ai_agents.add_remediation_plans(
        ALERT_ID, [newer_plan, older_plan]
    )
    google_chronicle_ai_agents.add_remediation_plan_details(102, newer_plan)
    set_is_first_run_to_true()

    remediation_agent.main()

    assert action_output.results.execution_state == ExecutionState.IN_PROGRESS
    assert (
        action_output.results.output_message
        == "Remediation job 102 awaits analyst approval or execution trigger."
    )


@set_metadata(
    integration_config=common.CONFIG,
)
def test_remediation_agent_first_run_latest_terminal_plan_triggers_new_even_if_older_active_exists(
    google_chronicle_ai_agents: GoogleSecOpsAiAgents,
    script_session: GoogleSecOpsAiAgentsSession,
    action_output: MockActionOutput,
) -> None:
    """Test that if the latest plan is terminal/ERROR, a new plan is triggered even if an older plan was active."""
    google_chronicle_ai_agents.cleanup_remediation()
    older_plan = dict(PLAN_DATA["plan_suggested_awaiting_approval"])
    older_plan["name"] = "projects/secops-prod/locations/us-central1/instances/siem-instance-1/remediationPlans/101"
    older_plan["createTime"] = "2026-09-01T10:00:00Z"

    newer_plan = dict(PLAN_DATA["plan_error"])
    newer_plan["name"] = "projects/secops-prod/locations/us-central1/instances/siem-instance-1/remediationPlans/102"
    newer_plan["createTime"] = "2026-09-07T12:00:00Z"

    # Newer plan is at index 0 (latest), but in ERROR state
    google_chronicle_ai_agents.add_remediation_plans(
        ALERT_ID, [newer_plan, older_plan]
    )
    google_chronicle_ai_agents.add_generated_remediation_plan(
        ALERT_ID, PLAN_DATA["generated_plan"]
    )
    set_is_first_run_to_true()

    remediation_agent.main()

    # Must NOT attach to older active plan 101; must trigger new plan
    assert action_output.results.execution_state == ExecutionState.IN_PROGRESS
    assert action_output.results.output_message == (
        f"Successfully triggered remediation job: {PLAN_NAME}"
    )


@set_metadata(
    integration_config=common.CONFIG,
)
def test_remediation_agent_first_run_terminal_plan_generates_new(
    google_chronicle_ai_agents: GoogleSecOpsAiAgents,
    script_session: GoogleSecOpsAiAgentsSession,
    action_output: MockActionOutput,
) -> None:
    """Test first run with an existing terminal/ERROR plan triggers new generation."""
    google_chronicle_ai_agents.cleanup_remediation()
    errored_plan = PLAN_DATA["plan_error"]
    google_chronicle_ai_agents.add_remediation_plans(ALERT_ID, [errored_plan])
    google_chronicle_ai_agents.add_generated_remediation_plan(
        ALERT_ID, PLAN_DATA["generated_plan"]
    )
    set_is_first_run_to_true()

    remediation_agent.main()

    assert action_output.results.execution_state == ExecutionState.IN_PROGRESS
    assert action_output.results.output_message == (
        f"Successfully triggered remediation job: {PLAN_NAME}"
    )


@set_metadata(
    integration_config=common.CONFIG,
    external_context=MockExternalContext(JOB_CONTEXT),
)
def test_remediation_agent_polling_plan_generating(
    google_chronicle_ai_agents: GoogleSecOpsAiAgents,
    script_session: GoogleSecOpsAiAgentsSession,
    action_output: MockActionOutput,
) -> None:
    """Test polling when plan generation is still in progress (REQUESTED)."""
    google_chronicle_ai_agents.cleanup_remediation()
    google_chronicle_ai_agents.add_remediation_plan_details(
        PLAN_NAME, PLAN_DATA["plan_generating"]
    )
    set_is_first_run_to_false()

    remediation_agent.main()

    assert action_output.results.execution_state == ExecutionState.IN_PROGRESS
    assert action_output.results.output_message == (
        f"Remediation job {PLAN_NAME} is still running (Status: Requested)"
    )


@set_metadata(
    integration_config=common.CONFIG,
    external_context=MockExternalContext(JOB_CONTEXT),
)
def test_remediation_agent_polling_awaiting_approval(
    google_chronicle_ai_agents: GoogleSecOpsAiAgents,
    script_session: GoogleSecOpsAiAgentsSession,
    action_output: MockActionOutput,
) -> None:
    """Test polling when plan is suggested but awaits analyst approval."""
    google_chronicle_ai_agents.cleanup_remediation()
    google_chronicle_ai_agents.add_remediation_plan_details(
        PLAN_NAME, PLAN_DATA["plan_suggested_awaiting_approval"]
    )
    set_is_first_run_to_false()

    remediation_agent.main()

    assert action_output.results.execution_state == ExecutionState.IN_PROGRESS
    assert "awaits analyst approval" in action_output.results.output_message


@set_metadata(
    integration_config=common.CONFIG,
    external_context=MockExternalContext(JOB_CONTEXT),
)
def test_remediation_agent_polling_execution_in_progress(
    google_chronicle_ai_agents: GoogleSecOpsAiAgents,
    script_session: GoogleSecOpsAiAgentsSession,
    action_output: MockActionOutput,
) -> None:
    """Test polling when plan execution is actively running (IN_PROGRESS)."""
    google_chronicle_ai_agents.cleanup_remediation()
    google_chronicle_ai_agents.add_remediation_plan_details(
        PLAN_NAME, PLAN_DATA["plan_approved_in_progress"]
    )
    google_chronicle_ai_agents.add_remediation_action_executions(
        PLAN_NAME, EXEC_DATA["in_progress"]["remediationActionExecutions"]
    )
    set_is_first_run_to_false()

    remediation_agent.main()

    assert action_output.results.execution_state == ExecutionState.IN_PROGRESS
    assert action_output.results.output_message == (
        f"Remediation job {PLAN_NAME} is still running (Status: In Progress)"
    )


@set_metadata(
    integration_config=common.CONFIG,
    external_context=MockExternalContext(JOB_CONTEXT),
)
def test_remediation_agent_polling_completed_success(
    google_chronicle_ai_agents: GoogleSecOpsAiAgents,
    script_session: GoogleSecOpsAiAgentsSession,
    action_output: MockActionOutput,
) -> None:
    """Test polling when plan execution has completed successfully (EXECUTED)."""
    google_chronicle_ai_agents.cleanup_remediation()
    plan_completed = PLAN_DATA["plan_completed_success"]
    execs = EXEC_DATA["success"]["remediationActionExecutions"]
    google_chronicle_ai_agents.add_remediation_plan_details(
        PLAN_NAME, plan_completed
    )
    google_chronicle_ai_agents.add_remediation_action_executions(
        PLAN_NAME, execs
    )
    set_is_first_run_to_false()

    remediation_agent.main()

    assert action_output.results.execution_state == ExecutionState.COMPLETED
    assert action_output.results.result_value is True
    assert (
        action_output.results.output_message
        == "Remediation job successfully ended with status: Executed"
    )
    assert (
        action_output.results.json_output.json_result["status"]
        == "REMEDIATION_PLAN_EXECUTION_STATE_EXECUTED"
    )
    assert (
        len(action_output.results.json_output.json_result["action_executions"])
        == 2
    )


@set_metadata(
    integration_config=common.CONFIG,
    external_context=MockExternalContext(JOB_CONTEXT),
)
def test_remediation_agent_polling_plan_error_fails(
    google_chronicle_ai_agents: GoogleSecOpsAiAgents,
    script_session: GoogleSecOpsAiAgentsSession,
    action_output: MockActionOutput,
) -> None:
    """Test polling when plan generation fails with ERROR state."""
    google_chronicle_ai_agents.cleanup_remediation()
    plan_error = PLAN_DATA["plan_error"]
    google_chronicle_ai_agents.add_remediation_plan_details(
        PLAN_NAME, plan_error
    )
    set_is_first_run_to_false()

    remediation_agent.main()

    assert action_output.results.execution_state == ExecutionState.FAILED
    assert action_output.results.result_value is False
    assert (
        plan_error["statusDetails"] in action_output.results.output_message
    )
    assert (
        action_output.results.json_output.json_result["status"]
        == "REMEDIATION_PLAN_STATE_ERROR"
    )


@set_metadata(
    integration_config=common.CONFIG,
    external_context=MockExternalContext(JOB_CONTEXT),
)
def test_remediation_agent_polling_plan_declined_fails(
    google_chronicle_ai_agents: GoogleSecOpsAiAgents,
    script_session: GoogleSecOpsAiAgentsSession,
    action_output: MockActionOutput,
) -> None:
    """Test polling when plan is declined by analyst."""
    google_chronicle_ai_agents.cleanup_remediation()
    plan_declined = PLAN_DATA["plan_declined"]
    google_chronicle_ai_agents.add_remediation_plan_details(
        PLAN_NAME, plan_declined
    )
    set_is_first_run_to_false()

    remediation_agent.main()

    assert action_output.results.execution_state == ExecutionState.FAILED
    assert action_output.results.result_value is False
    assert "declined" in action_output.results.output_message.lower()
    assert (
        action_output.results.json_output.json_result["status"]
        == "REMEDIATION_PLAN_STATE_DECLINED"
    )


@set_metadata(
    integration_config=common.CONFIG,
    external_context=MockExternalContext(JOB_CONTEXT),
)
def test_remediation_agent_polling_execution_rejected_fails(
    google_chronicle_ai_agents: GoogleSecOpsAiAgents,
    script_session: GoogleSecOpsAiAgentsSession,
    action_output: MockActionOutput,
) -> None:
    """Test polling when plan execution run fails / is rejected."""
    google_chronicle_ai_agents.cleanup_remediation()
    plan_failed = PLAN_DATA["plan_execution_failed"]
    execs = EXEC_DATA["failure"]["remediationActionExecutions"]
    google_chronicle_ai_agents.add_remediation_plan_details(
        PLAN_NAME, plan_failed
    )
    google_chronicle_ai_agents.add_remediation_action_executions(
        PLAN_NAME, execs
    )
    set_is_first_run_to_false()

    remediation_agent.main()

    assert action_output.results.execution_state == ExecutionState.FAILED
    assert action_output.results.result_value is False
    assert (
        action_output.results.output_message
        == "Remediation job ended with non-success status: Rejected"
    )
    assert (
        action_output.results.json_output.json_result["status"]
        == "REMEDIATION_PLAN_EXECUTION_STATE_REJECTED"
    )


@set_metadata(
    integration_config=common.CONFIG,
)
def test_remediation_agent_missing_alert_id_fails(
    google_chronicle_ai_agents: GoogleSecOpsAiAgents,
    script_session: GoogleSecOpsAiAgentsSession,
    action_output: MockActionOutput,
) -> None:
    """Test alert validation failure when alert lacks SIEM Alert ID."""
    set_is_first_run_to_true()
    with patch.object(
        SiemplifyAction,
        "current_alert",
        new_callable=PropertyMock,
        return_value=MagicMock(additional_properties={}, identifier=None),
    ):
        remediation_agent.main()

    assert action_output.results.execution_state == ExecutionState.FAILED
    assert action_output.results.result_value is False
    assert (
        action_output.results.output_message == ALERT_NOT_FROM_SIEM_MESSAGE
    )


@set_metadata(
    integration_config=common.CONFIG,
    external_context=MockExternalContext(JOB_CONTEXT),
)
def test_remediation_agent_entire_workflow_lifecycle(
    google_chronicle_ai_agents: GoogleSecOpsAiAgents,
    script_session: GoogleSecOpsAiAgentsSession,
    action_output: MockActionOutput,
) -> None:
    """Test the entire multi-cycle remediation workflow from first run to final result."""
    google_chronicle_ai_agents.cleanup_remediation()

    # --- CYCLE 1: Intake (First Run) -> Triggers new plan ---
    google_chronicle_ai_agents.add_remediation_plans(ALERT_ID, [])
    google_chronicle_ai_agents.add_generated_remediation_plan(
        ALERT_ID, PLAN_DATA["generated_plan"]
    )
    set_is_first_run_to_true()

    remediation_agent.main()

    assert action_output.results.execution_state == ExecutionState.IN_PROGRESS
    assert action_output.results.output_message == (
        f"Successfully triggered remediation job: {PLAN_NAME}"
    )
    action_output.flush()

    # --- CYCLE 2: Polling -> Plan Generation In Progress (REQUESTED) ---
    google_chronicle_ai_agents.add_remediation_plan_details(
        PLAN_NAME, PLAN_DATA["plan_generating"]
    )
    set_is_first_run_to_false()

    remediation_agent.main()

    assert action_output.results.execution_state == ExecutionState.IN_PROGRESS
    assert action_output.results.output_message == (
        f"Remediation job {PLAN_NAME} is still running (Status: Requested)"
    )
    action_output.flush()

    # --- CYCLE 3: Polling -> Plan Suggested, Awaiting Analyst Review ---
    google_chronicle_ai_agents.add_remediation_plan_details(
        PLAN_NAME, PLAN_DATA["plan_suggested_awaiting_approval"]
    )

    remediation_agent.main()

    assert action_output.results.execution_state == ExecutionState.IN_PROGRESS
    assert (
        action_output.results.output_message
        == f"Remediation job {PLAN_NAME} awaits analyst approval or execution trigger."
    )
    action_output.flush()

    # --- CYCLE 4: Polling -> Plan Approved, Execution In Progress ---
    google_chronicle_ai_agents.add_remediation_plan_details(
        PLAN_NAME, PLAN_DATA["plan_approved_in_progress"]
    )
    google_chronicle_ai_agents.add_remediation_action_executions(
        PLAN_NAME, EXEC_DATA["in_progress"]["remediationActionExecutions"]
    )

    remediation_agent.main()

    assert action_output.results.execution_state == ExecutionState.IN_PROGRESS
    assert action_output.results.output_message == (
        f"Remediation job {PLAN_NAME} is still running (Status: In Progress)"
    )
    action_output.flush()

    # --- CYCLE 5: Polling -> Plan Execution Completed Successfully ---
    plan_completed = PLAN_DATA["plan_completed_success"]
    execs = EXEC_DATA["success"]["remediationActionExecutions"]
    google_chronicle_ai_agents.add_remediation_plan_details(
        PLAN_NAME, plan_completed
    )
    google_chronicle_ai_agents.add_remediation_action_executions(
        PLAN_NAME, execs
    )

    remediation_agent.main()

    assert action_output.results.execution_state == ExecutionState.COMPLETED
    assert action_output.results.result_value is True
    assert (
        action_output.results.output_message
        == "Remediation job successfully ended with status: Executed"
    )
    assert (
        action_output.results.json_output.json_result["status"]
        == "REMEDIATION_PLAN_EXECUTION_STATE_EXECUTED"
    )
    assert (
        len(action_output.results.json_output.json_result["action_executions"])
        == 2
    )


@set_metadata(
    integration_config=common.CONFIG,
    parameters={"additional_data": json.dumps({"plan_id": PLAN_NAME})},
)
def test_remediation_agent_polling_reads_plan_id_from_additional_data(
    google_chronicle_ai_agents: GoogleSecOpsAiAgents,
    script_session: GoogleSecOpsAiAgentsSession,
    action_output: MockActionOutput,
) -> None:
    """Test polling reads plan_id directly from additional_data action parameter."""
    google_chronicle_ai_agents.cleanup_remediation()
    google_chronicle_ai_agents.add_remediation_plan_details(
        PLAN_NAME, PLAN_DATA["plan_generating"]
    )
    set_is_first_run_to_false()

    remediation_agent.main()

    assert action_output.results.execution_state == ExecutionState.IN_PROGRESS
    assert action_output.results.output_message == (
        f"Remediation job {PLAN_NAME} is still running (Status: Requested)"
    )
    assert action_output.results.result_value is True


@set_metadata(
    integration_config=common.CONFIG,
    parameters={"additional_data": json.dumps({"plan_id": PLAN_NAME})},
)
def test_remediation_agent_polling_unexpected_plan_state_fails(
    google_chronicle_ai_agents: GoogleSecOpsAiAgents,
    script_session: GoogleSecOpsAiAgentsSession,
    action_output: MockActionOutput,
) -> None:
    """Test polling immediately fails if plan has unexpected state (e.g. UNSPECIFIED)."""
    google_chronicle_ai_agents.cleanup_remediation()
    unspecified_plan = {
        **PLAN_DATA["plan_generating"],
        "state": "REMEDIATION_PLAN_STATE_UNSPECIFIED",
    }
    google_chronicle_ai_agents.add_remediation_plan_details(
        PLAN_NAME, unspecified_plan
    )
    set_is_first_run_to_false()

    remediation_agent.main()

    assert action_output.results.execution_state == ExecutionState.FAILED
    assert action_output.results.output_message == (
        "Remediation job ended with unexpected status: Unspecified"
    )
    assert action_output.results.result_value is False
    assert action_output.results.json_output.json_result["status"] == "REMEDIATION_PLAN_STATE_UNSPECIFIED"
