from __future__ import annotations

from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata
from TIPCommon.base.action import ExecutionState

from ..common import CONFIG_PATH, load_action
from ..core.product import Infoblox
from ..core.session import InfobloxSession

UndoARecommendationAction = load_action("undo_a_recommendation_action")


class TestUndoARecommendationAction:
    @set_metadata(parameters={"Audit Entry ID": "audit-1"}, integration_config_file_path=CONFIG_PATH)
    def test_success(
        self,
        script_session: InfobloxSession,
        action_output: MockActionOutput,
        infoblox: Infoblox,
    ) -> None:
        infoblox.set_undo_recommendation_response({"result": {"status": "success", "action": "Yes"}})

        UndoARecommendationAction.main()

        assert any(
            r.request.method.value == "POST"
            and r.request.url.path.endswith("/api/v2/insights/global-activity/audit-1/undo")
            for r in script_session.request_history
        )
        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert "Successfully undone the action for Audit Entry ID 'audit-1'" in action_output.results.output_message

    @set_metadata(parameters={"Audit Entry ID": "audit-1"}, integration_config_file_path=CONFIG_PATH)
    def test_failed_result_marks_action_failed(
        self,
        script_session: InfobloxSession,
        action_output: MockActionOutput,
        infoblox: Infoblox,
    ) -> None:
        infoblox.set_undo_recommendation_response({"result": {"status": "failed", "message": "Cannot undo"}})

        UndoARecommendationAction.main()

        assert action_output.results.execution_state == ExecutionState.FAILED
        assert "Cannot undo" in action_output.results.output_message

    @set_metadata(parameters={"Audit Entry ID": "missing-audit"}, integration_config_file_path=CONFIG_PATH)
    def test_audit_entry_not_found_fails(
        self,
        script_session: InfobloxSession,
        action_output: MockActionOutput,
        infoblox: Infoblox,
    ) -> None:
        with infoblox.fail_requests(status_code=404):
            UndoARecommendationAction.main()

        assert action_output.results.execution_state == ExecutionState.FAILED
        assert "Audit entry doesn't exist." in action_output.results.output_message

    @set_metadata(parameters={"Audit Entry ID": "audit-1"}, integration_config_file_path=CONFIG_PATH)
    def test_action_cannot_be_undone_fails_with_400_message(
        self,
        script_session: InfobloxSession,
        action_output: MockActionOutput,
        infoblox: Infoblox,
    ) -> None:
        with infoblox.fail_requests(status_code=400, body={"message": "Already undone"}):
            UndoARecommendationAction.main()

        assert action_output.results.execution_state == ExecutionState.FAILED
        assert "Already undone" in action_output.results.output_message

    @set_metadata(parameters={"Audit Entry ID": "audit-1"}, integration_config_file_path=CONFIG_PATH)
    def test_action_cannot_be_undone_fails_with_default_400_message(
        self,
        script_session: InfobloxSession,
        action_output: MockActionOutput,
        infoblox: Infoblox,
    ) -> None:
        with infoblox.fail_requests(status_code=400, body={}):
            UndoARecommendationAction.main()

        assert action_output.results.execution_state == ExecutionState.FAILED
        assert "The action cannot be undone." in action_output.results.output_message
