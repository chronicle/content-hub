from __future__ import annotations

from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata
from TIPCommon.base.action import ExecutionState

from ..common import CONFIG_PATH, load_action
from ..core.product import Infoblox
from ..core.session import InfobloxSession

GetInfobloxIQIndicators = load_action("get_infoblox_iq_for_threat_defense_indicators")


class TestGetInfobloxIQForThreatDefenseIndicators:
    @set_metadata(parameters={"Insight ID": "insight-1"}, integration_config_file_path=CONFIG_PATH)
    def test_success(
        self,
        script_session: InfobloxSession,
        action_output: MockActionOutput,
        infoblox: Infoblox,
    ) -> None:
        infoblox.set_insights_indicators_response({
            "indicators": [{"threat_indicator": "evil.com", "threat_level": "HIGH"}]
        })

        GetInfobloxIQIndicators.main()

        assert any(
            r.request.url.path.endswith("/api/v2/insights/insight-1/indicators") for r in script_session.request_history
        )
        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert "Successfully retrieved 1 indicator(s)" in action_output.results.output_message

    @set_metadata(parameters={"Insight ID": "insight-1"}, integration_config_file_path=CONFIG_PATH)
    def test_no_indicators_found(
        self,
        script_session: InfobloxSession,
        action_output: MockActionOutput,
        infoblox: Infoblox,
    ) -> None:
        infoblox.set_insights_indicators_response({"indicators": []})

        GetInfobloxIQIndicators.main()

        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert "No indicators found" in action_output.results.output_message

    @set_metadata(parameters={"Insight ID": "missing-insight"}, integration_config_file_path=CONFIG_PATH)
    def test_insight_not_found_fails(
        self,
        script_session: InfobloxSession,
        action_output: MockActionOutput,
        infoblox: Infoblox,
    ) -> None:
        with infoblox.fail_requests(status_code=404):
            GetInfobloxIQIndicators.main()

        assert action_output.results.execution_state == ExecutionState.FAILED
        assert "Insight doesn't exist." in action_output.results.output_message

    @set_metadata(
        parameters={"Insight ID": "insight-1", "Detected At": "not-a-date"},
        integration_config_file_path=CONFIG_PATH,
    )
    def test_invalid_detected_at_fails(
        self,
        script_session: InfobloxSession,
        action_output: MockActionOutput,
        infoblox: Infoblox,
    ) -> None:
        GetInfobloxIQIndicators.main()

        assert action_output.results.execution_state == ExecutionState.FAILED
