from __future__ import annotations

from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata

from cyware_intel_exchange.actions import create_intel_in_cyware_intel_exchange
from cyware_intel_exchange.tests.common import (
    CONFIG_PATH,
    MOCK_CREATE_INTEL,
    MOCK_QUICK_INTEL_STATUS,
)
from cyware_intel_exchange.tests.core.product import CywareIntelExchange
from cyware_intel_exchange.tests.core.session import CywareSession

DEFAULT_PARAMETERS = {
    "IOC Type": "domain-name",
    "Title": "Test Intel",
    "Confidence": "90",
    "Threat Type": "malware",
}

DEFAULT_ENTITIES = [
    {"identifier": "malicious.com", "entity_type": "HOSTNAME", "additional_properties": {}},
    {"identifier": "evil.com", "entity_type": "HOSTNAME", "additional_properties": {}},
]


class TestCreateIntelInCywareIntelExchange:
    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        parameters=DEFAULT_PARAMETERS,
        entities=DEFAULT_ENTITIES,
    )
    def test_create_intel_success(
        self,
        script_session: CywareSession,
        action_output: MockActionOutput,
        cyware: CywareIntelExchange,
    ) -> None:
        cyware.create_intel_response = MOCK_CREATE_INTEL
        cyware.quick_intel_status_response = MOCK_QUICK_INTEL_STATUS
        success_output_msg_prefix = "Successfully created intel"

        create_intel_in_cyware_intel_exchange.main()

        assert len(script_session.request_history) >= 1
        assert success_output_msg_prefix in action_output.results.output_message
        assert action_output.results.result_value is True
        assert action_output.results.execution_state.value == 0
