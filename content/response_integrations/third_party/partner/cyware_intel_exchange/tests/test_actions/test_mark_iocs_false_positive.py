from __future__ import annotations

from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata

from cyware_intel_exchange.actions import mark_iocs_false_positive
from cyware_intel_exchange.tests.common import (
    CONFIG_PATH,
    MOCK_BULK_LOOKUP,
    MOCK_MARK_FALSE_POSITIVE,
)
from cyware_intel_exchange.tests.core.product import CywareIntelExchange
from cyware_intel_exchange.tests.core.session import CywareSession

DEFAULT_ENTITIES = [
    {"identifier": "malicious.com", "entity_type": "HOSTNAME", "additional_properties": {}},
    {"identifier": "evil.com", "entity_type": "HOSTNAME", "additional_properties": {}},
]


class TestMarkIOCsFalsePositive:
    @set_metadata(integration_config_file_path=CONFIG_PATH, entities=DEFAULT_ENTITIES)
    def test_mark_iocs_false_positive_success(
        self,
        script_session: CywareSession,
        action_output: MockActionOutput,
        cyware: CywareIntelExchange,
    ) -> None:
        cyware.bulk_lookup_response = MOCK_BULK_LOOKUP
        cyware.mark_false_positive_response = MOCK_MARK_FALSE_POSITIVE
        success_output_msg_prefix = "Successfully marked"

        mark_iocs_false_positive.main()

        assert len(script_session.request_history) >= 1
        assert success_output_msg_prefix in action_output.results.output_message
        assert action_output.results.result_value is True
        assert action_output.results.execution_state.value == 0
