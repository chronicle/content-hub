from __future__ import annotations

from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata

from cyware_intel_exchange.actions import remove_iocs_from_allowed_list
from cyware_intel_exchange.tests.common import (
    CONFIG_PATH,
    MOCK_BULK_LOOKUP,
    MOCK_REMOVE_ALLOWED_IOCS,
)
from cyware_intel_exchange.tests.core.product import CywareIntelExchange
from cyware_intel_exchange.tests.core.session import CywareSession

DEFAULT_ENTITIES = [
    {"identifier": "192.168.1.100", "entity_type": "ADDRESS", "additional_properties": {}},
    {"identifier": "10.0.0.1", "entity_type": "ADDRESS", "additional_properties": {}},
]


class TestRemoveIOCsFromAllowedList:
    @set_metadata(integration_config_file_path=CONFIG_PATH, entities=DEFAULT_ENTITIES)
    def test_remove_iocs_from_allowed_list_success(
        self,
        script_session: CywareSession,
        action_output: MockActionOutput,
        cyware: CywareIntelExchange,
    ) -> None:
        cyware.bulk_lookup_response = MOCK_BULK_LOOKUP
        cyware.remove_allowed_iocs_response = MOCK_REMOVE_ALLOWED_IOCS
        success_output_msg_prefix = "Successfully removed"

        remove_iocs_from_allowed_list.main()

        assert len(script_session.request_history) >= 1
        assert success_output_msg_prefix in action_output.results.output_message
        assert action_output.results.result_value is True
        assert action_output.results.execution_state.value == 0
