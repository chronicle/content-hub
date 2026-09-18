from __future__ import annotations

from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata
from TIPCommon.base.action import ExecutionState

from ..common import CONFIG_PATH, load_action
from ..core.product import Infoblox
from ..core.session import InfobloxSession

UpdateStatusOfInsight = load_action("update_status_of_infoblox_iq_for_threat_defense")


class TestUpdateStatusOfInfobloxIQForThreatDefense:
    @set_metadata(
        parameters={"Insight ID": "insight-1", "Status": "In Progress", "Comment": "Investigating"},
        integration_config_file_path=CONFIG_PATH,
    )
    def test_success(
        self,
        script_session: InfobloxSession,
        action_output: MockActionOutput,
        infoblox: Infoblox,
    ) -> None:
        UpdateStatusOfInsight.main()

        assert any(
            r.request.method.value == "PUT" and r.request.url.path.endswith("/api/v2/insights/status")
            for r in script_session.request_history
        )
        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert "to 'In Progress'" in action_output.results.output_message

    @set_metadata(
        parameters={"Insight ID": "insight-1", "Status": "Not A Real Status"},
        integration_config_file_path=CONFIG_PATH,
    )
    def test_invalid_status_fails(
        self,
        script_session: InfobloxSession,
        action_output: MockActionOutput,
        infoblox: Infoblox,
    ) -> None:
        UpdateStatusOfInsight.main()

        assert action_output.results.execution_state == ExecutionState.FAILED

    @set_metadata(
        parameters={"Insight ID": "missing-insight", "Status": "Resolved"},
        integration_config_file_path=CONFIG_PATH,
    )
    def test_insight_not_found_fails(
        self,
        script_session: InfobloxSession,
        action_output: MockActionOutput,
        infoblox: Infoblox,
    ) -> None:
        with infoblox.fail_requests(status_code=404):
            UpdateStatusOfInsight.main()

        assert action_output.results.execution_state == ExecutionState.FAILED
        assert "Insight doesn't exist." in action_output.results.output_message
