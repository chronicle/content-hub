from __future__ import annotations

from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata
from TIPCommon.base.action import ExecutionState

from ..common import CONFIG_PATH, load_action
from ..core.product import Infoblox
from ..core.session import InfobloxSession

HostLookup = load_action("host_lookup")


class TestHostLookup:
    @set_metadata(integration_config_file_path=CONFIG_PATH)
    def test_success_with_results(
        self,
        script_session: InfobloxSession,
        action_output: MockActionOutput,
        infoblox: Infoblox,
    ) -> None:
        infoblox.set_host_lookup_response({
            "results": [{"id": "h1", "name": "host1", "addresses": [{"address": "10.0.0.5"}]}]
        })

        HostLookup.main()

        assert any(r.request.url.path.endswith("/api/ddi/v1/ipam/host") for r in script_session.request_history)
        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert "Successfully retrieved 1 host asset record" in action_output.results.output_message

    @set_metadata(integration_config_file_path=CONFIG_PATH)
    def test_no_results_found(
        self,
        script_session: InfobloxSession,
        action_output: MockActionOutput,
        infoblox: Infoblox,
    ) -> None:
        infoblox.set_host_lookup_response({"results": []})

        HostLookup.main()

        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert action_output.results.output_message == "No host asset records found."

    @set_metadata(integration_config_file_path=CONFIG_PATH)
    def test_api_failure(
        self,
        script_session: InfobloxSession,
        action_output: MockActionOutput,
        infoblox: Infoblox,
    ) -> None:
        with infoblox.fail_requests(status_code=500):
            HostLookup.main()

        assert action_output.results.execution_state == ExecutionState.FAILED
