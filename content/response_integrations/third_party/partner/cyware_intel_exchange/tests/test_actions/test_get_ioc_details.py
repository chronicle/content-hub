from __future__ import annotations

from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata

from cyware_intel_exchange.actions import get_ioc_details
from cyware_intel_exchange.tests.common import CONFIG_PATH, MOCK_GET_IOC_DETAILS
from cyware_intel_exchange.tests.core.product import CywareIntelExchange
from cyware_intel_exchange.tests.core.session import CywareSession

DEFAULT_PARAMETERS = {
    "Max Results to Return": "10",
}

DEFAULT_ENTITIES = [
    {"identifier": "malicious.com", "entity_type": "HOSTNAME", "additional_properties": {}},
    {"identifier": "evil.com", "entity_type": "HOSTNAME", "additional_properties": {}},
]


class TestGetIOCDetails:
    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        parameters=DEFAULT_PARAMETERS,
        entities=DEFAULT_ENTITIES,
    )
    def test_get_ioc_details_success(
        self,
        script_session: CywareSession,
        action_output: MockActionOutput,
        cyware: CywareIntelExchange,
    ) -> None:
        cyware.bulk_lookup_response = MOCK_GET_IOC_DETAILS
        success_output_msg_prefix = "Successfully retrieved details"

        get_ioc_details.main()

        assert len(script_session.request_history) >= 1
        assert success_output_msg_prefix in action_output.results.output_message
        assert action_output.results.result_value is True
        assert action_output.results.execution_state.value == 0
