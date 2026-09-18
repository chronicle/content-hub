from __future__ import annotations

from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata
from TIPCommon.base.action import ExecutionState

from ..common import CONFIG_PATH, load_action
from ..core.product import Infoblox
from ..core.session import InfobloxSession

ExecuteRecommendationActions = load_action("execute_recommendation_actions")


class TestExecuteRecommendationActions:
    @set_metadata(
        parameters={"Insight ID": "insight-1", "Recommendation Id": "rec-1"},
        integration_config_file_path=CONFIG_PATH,
    )
    def test_success(
        self,
        script_session: InfobloxSession,
        action_output: MockActionOutput,
        infoblox: Infoblox,
    ) -> None:
        infoblox.set_recommendation_action_response({
            "results": [{"action": "Yes", "status": "success", "audit_entry_id": "audit-1"}]
        })

        ExecuteRecommendationActions.main()

        assert any(
            r.request.method.value == "POST" and r.request.url.path.endswith("/api/v2/insights/insight-1/actions")
            for r in script_session.request_history
        )
        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert "Successfully executed Recommendation Id 'rec-1'" in action_output.results.output_message

    @set_metadata(
        parameters={"Insight ID": "insight-1", "Recommendation Id": "rec-1"},
        integration_config_file_path=CONFIG_PATH,
    )
    def test_failed_item_marks_action_failed(
        self,
        script_session: InfobloxSession,
        action_output: MockActionOutput,
        infoblox: Infoblox,
    ) -> None:
        infoblox.set_recommendation_action_response({
            "results": [{"action": "Yes", "status": "failed", "message": "Already applied"}]
        })

        ExecuteRecommendationActions.main()

        assert action_output.results.execution_state == ExecutionState.FAILED
        assert "Already applied" in action_output.results.output_message

    @set_metadata(
        parameters={"Insight ID": "insight-1", "Recommendation Id": "rec-1"},
        integration_config_file_path=CONFIG_PATH,
    )
    def test_no_results_returned_marks_action_success(
        self,
        script_session: InfobloxSession,
        action_output: MockActionOutput,
        infoblox: Infoblox,
    ) -> None:
        # No "Action" parameter exists on this action anymore — the recommendation's
        # action is resolved server-side, so an empty result set is not a failure.
        ExecuteRecommendationActions.main()

        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert "Successfully executed Recommendation Id 'rec-1'" in action_output.results.output_message

    @set_metadata(
        parameters={"Insight ID": "missing-insight", "Recommendation Id": "rec-1"},
        integration_config_file_path=CONFIG_PATH,
    )
    def test_insight_not_found_fails(
        self,
        script_session: InfobloxSession,
        action_output: MockActionOutput,
        infoblox: Infoblox,
    ) -> None:
        with infoblox.fail_requests(status_code=404):
            ExecuteRecommendationActions.main()

        assert action_output.results.execution_state == ExecutionState.FAILED
        assert "Insight doesn't exist." in action_output.results.output_message

    @set_metadata(
        parameters={"Insight ID": "insight-1", "Recommendation Id": "rec-1"},
        integration_config_file_path=CONFIG_PATH,
    )
    def test_bad_request_fails_with_400_message(
        self,
        script_session: InfobloxSession,
        action_output: MockActionOutput,
        infoblox: Infoblox,
    ) -> None:
        with infoblox.fail_requests(status_code=400, body={"message": "Recommendation already executed"}):
            ExecuteRecommendationActions.main()

        assert action_output.results.execution_state == ExecutionState.FAILED
        assert "Recommendation already executed" in action_output.results.output_message
