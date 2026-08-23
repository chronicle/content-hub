from __future__ import annotations

from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata
from TIPCommon.base.action import ExecutionState

from ..common import CONFIG_PATH, load_action
from ..core.product import Infoblox
from ..core.session import InfobloxSession

DHCPLeaseLookup = load_action("dhcp_lease_lookup")


class TestDHCPLeaseLookup:
    @set_metadata(integration_config_file_path=CONFIG_PATH)
    def test_success_with_results(
        self,
        script_session: InfobloxSession,
        action_output: MockActionOutput,
        infoblox: Infoblox,
    ) -> None:
        infoblox.set_dhcp_lease_response({"results": [{"address": "10.0.0.5", "hostname": "host1"}]})

        DHCPLeaseLookup.main()

        assert any(r.request.url.path.endswith("/api/ddi/v1/dhcp/lease") for r in script_session.request_history)
        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert "Successfully retrieved 1 DHCP lease record" in action_output.results.output_message

    @set_metadata(integration_config_file_path=CONFIG_PATH)
    def test_no_results_found(
        self,
        script_session: InfobloxSession,
        action_output: MockActionOutput,
        infoblox: Infoblox,
    ) -> None:
        infoblox.set_dhcp_lease_response({"results": []})

        DHCPLeaseLookup.main()

        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert action_output.results.output_message == "No DHCP lease records found."

    @set_metadata(integration_config_file_path=CONFIG_PATH)
    def test_api_failure(
        self,
        script_session: InfobloxSession,
        action_output: MockActionOutput,
        infoblox: Infoblox,
    ) -> None:
        with infoblox.fail_requests(status_code=500):
            DHCPLeaseLookup.main()

        assert action_output.results.execution_state == ExecutionState.FAILED
