from __future__ import annotations

from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata
from TIPCommon.base.action import ExecutionState

from ..common import CONFIG_PATH, load_action
from ..core.product import Infoblox
from ..core.session import InfobloxSession

IPLookup = load_action("ip_lookup")


class TestIPLookup:
    @set_metadata(integration_config_file_path=CONFIG_PATH)
    def test_success_with_results(
        self,
        script_session: InfobloxSession,
        action_output: MockActionOutput,
        infoblox: Infoblox,
    ) -> None:
        infoblox.set_ip_lookup_response({"results": [{"id": "ip1", "address": "10.0.0.5"}]})

        IPLookup.main()

        assert any(r.request.url.path.endswith("/api/ddi/v1/ipam/address") for r in script_session.request_history)
        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert "Successfully retrieved 1 IP records" in action_output.results.output_message

    @set_metadata(integration_config_file_path=CONFIG_PATH)
    def test_no_results_found(
        self,
        script_session: InfobloxSession,
        action_output: MockActionOutput,
        infoblox: Infoblox,
    ) -> None:
        infoblox.set_ip_lookup_response({"results": []})

        IPLookup.main()

        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert action_output.results.output_message == "No IP data found."

    @set_metadata(parameters={"Limit": "abc"}, integration_config_file_path=CONFIG_PATH)
    def test_invalid_limit_fails(
        self,
        script_session: InfobloxSession,
        action_output: MockActionOutput,
        infoblox: Infoblox,
    ) -> None:
        IPLookup.main()

        assert action_output.results.execution_state == ExecutionState.FAILED

    @set_metadata(integration_config_file_path=CONFIG_PATH)
    def test_api_failure(
        self,
        script_session: InfobloxSession,
        action_output: MockActionOutput,
        infoblox: Infoblox,
    ) -> None:
        with infoblox.fail_requests(status_code=500):
            IPLookup.main()

        assert action_output.results.execution_state == ExecutionState.FAILED
