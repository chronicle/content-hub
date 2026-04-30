from __future__ import annotations

from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata

from cyware_intel_exchange.actions import ping
from cyware_intel_exchange.tests.common import CONFIG_PATH
from cyware_intel_exchange.tests.core.product import CywareIntelExchange
from cyware_intel_exchange.tests.core.session import CywareSession


class TestPing:
    @set_metadata(integration_config_file_path=CONFIG_PATH)
    def test_ping_success(
        self,
        script_session: CywareSession,
        action_output: MockActionOutput,
        cyware: CywareIntelExchange,
    ) -> None:
        success_output_msg = "Successfully connected to the Cyware server!"

        ping.main()

        assert len(script_session.request_history) >= 1
        assert action_output.results.output_message == success_output_msg
        assert action_output.results.result_value is True
        assert action_output.results.execution_state.value == 0
