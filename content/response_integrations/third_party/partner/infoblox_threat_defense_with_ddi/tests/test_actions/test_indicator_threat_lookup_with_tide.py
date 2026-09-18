from __future__ import annotations

from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata
from TIPCommon.base.action import ExecutionState

from ..common import CONFIG_PATH, load_action
from ..core.product import Infoblox
from ..core.session import InfobloxSession

IndicatorThreatLookupWithTIDE = load_action("indicator_threat_lookup_with_tide")


class TestIndicatorThreatLookupWithTIDE:
    @set_metadata(
        parameters={"Indicator Type": "Host", "Indicator Value": "evil.example.com"},
        integration_config_file_path=CONFIG_PATH,
    )
    def test_success(
        self,
        script_session: InfobloxSession,
        action_output: MockActionOutput,
        infoblox: Infoblox,
    ) -> None:
        infoblox.set_tide_response({"threat": [{"type": "HOST", "host": "evil.example.com", "threat_level": "HIGH"}]})

        IndicatorThreatLookupWithTIDE.main()

        assert any(r.request.url.path.endswith("/tide/api/data/threats") for r in script_session.request_history)
        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert "Successfully retrieved 1 TIDE threat record" in action_output.results.output_message

    @set_metadata(integration_config_file_path=CONFIG_PATH)
    def test_no_data_found(
        self,
        script_session: InfobloxSession,
        action_output: MockActionOutput,
        infoblox: Infoblox,
    ) -> None:
        infoblox.set_tide_response({"threat": []})

        IndicatorThreatLookupWithTIDE.main()

        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert action_output.results.output_message == "No TIDE threat data found."

    @set_metadata(parameters={"Limit": "not-an-int"}, integration_config_file_path=CONFIG_PATH)
    def test_invalid_limit_fails(
        self,
        script_session: InfobloxSession,
        action_output: MockActionOutput,
        infoblox: Infoblox,
    ) -> None:
        IndicatorThreatLookupWithTIDE.main()

        assert action_output.results.execution_state == ExecutionState.FAILED

    @set_metadata(integration_config_file_path=CONFIG_PATH)
    def test_api_failure_bad_request(
        self,
        script_session: InfobloxSession,
        action_output: MockActionOutput,
        infoblox: Infoblox,
    ) -> None:
        with infoblox.fail_requests(status_code=400, body={"message": "Invalid TIDE query"}):
            IndicatorThreatLookupWithTIDE.main()

        assert action_output.results.execution_state == ExecutionState.FAILED
        assert "Invalid TIDE query" in action_output.results.output_message
