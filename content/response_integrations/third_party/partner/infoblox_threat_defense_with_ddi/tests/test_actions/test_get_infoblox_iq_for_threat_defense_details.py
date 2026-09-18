from __future__ import annotations

from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata
from TIPCommon.base.action import ExecutionState

from ..common import CONFIG_PATH, load_action
from ..core.product import Infoblox
from ..core.session import InfobloxSession

GetInfobloxIQDetails = load_action("get_infoblox_iq_for_threat_defense_details")


class TestGetInfobloxIQForThreatDefenseDetails:
    @set_metadata(parameters={"Insight ID": "insight-1"}, integration_config_file_path=CONFIG_PATH)
    def test_success(
        self,
        script_session: InfobloxSession,
        action_output: MockActionOutput,
        infoblox: Infoblox,
    ) -> None:
        infoblox.set_insight_details_response({"insight_id": "insight-1", "name": "Insight One", "severity": "HIGH"})

        GetInfobloxIQDetails.main()

        assert any(r.request.url.path.endswith("/api/v2/insights/insight-1") for r in script_session.request_history)
        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert "Successfully retrieved details for Insight ID 'insight-1'" in action_output.results.output_message

    @set_metadata(parameters={"Insight ID": "missing-insight"}, integration_config_file_path=CONFIG_PATH)
    def test_insight_not_found_fails(
        self,
        script_session: InfobloxSession,
        action_output: MockActionOutput,
        infoblox: Infoblox,
    ) -> None:
        with infoblox.fail_requests(status_code=404):
            GetInfobloxIQDetails.main()

        assert action_output.results.execution_state == ExecutionState.FAILED
        assert "Insight doesn't exist." in action_output.results.output_message
