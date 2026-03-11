from __future__ import annotations

from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata

from cyware_intel_exchange.actions import get_allowed_iocs
from cyware_intel_exchange.tests.common import CONFIG_PATH, MOCK_GET_ALLOWED_IOCS
from cyware_intel_exchange.tests.core.product import CywareIntelExchange
from cyware_intel_exchange.tests.core.session import CywareSession

DEFAULT_PARAMETERS = {
    "Max Results to Return": "10",
}


class TestGetAllowedIOCs:
    @set_metadata(integration_config_file_path=CONFIG_PATH, parameters=DEFAULT_PARAMETERS)
    def test_get_allowed_iocs_success(
        self,
        script_session: CywareSession,
        action_output: MockActionOutput,
        cyware: CywareIntelExchange,
    ) -> None:
        cyware.get_allowed_iocs_response = MOCK_GET_ALLOWED_IOCS
        success_output_msg_prefix = "Successfully retrieved"

        get_allowed_iocs.main()

        assert len(script_session.request_history) >= 1
        assert success_output_msg_prefix in action_output.results.output_message
        assert action_output.results.result_value is True
        assert action_output.results.execution_state.value == 0
