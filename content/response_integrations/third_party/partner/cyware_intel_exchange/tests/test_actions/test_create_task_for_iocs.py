from __future__ import annotations

from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata

from cyware_intel_exchange.actions import create_task_for_iocs
from cyware_intel_exchange.tests.common import (
    CONFIG_PATH,
    MOCK_BULK_LOOKUP,
    MOCK_CREATE_TASK,
    MOCK_GET_USER_BY_EMAIL,
)
from cyware_intel_exchange.tests.core.product import CywareIntelExchange
from cyware_intel_exchange.tests.core.session import CywareSession

DEFAULT_PARAMETERS = {
    "Text": "Investigate this IOC for potential threats",
    "Priority": "high",
    "Status": "not_started",
    "Deadline": "7",
    "Assignee Email ID": "test@example.com",
}

DEFAULT_ENTITIES = [
    {"identifier": "malicious.com", "entity_type": "HOSTNAME", "additional_properties": {}},
    {"identifier": "evil.com", "entity_type": "HOSTNAME", "additional_properties": {}},
]


class TestCreateTaskForIOCs:
    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        parameters=DEFAULT_PARAMETERS,
        entities=DEFAULT_ENTITIES,
    )
    def test_create_task_for_iocs_success_with_assignee(
        self,
        script_session: CywareSession,
        action_output: MockActionOutput,
        cyware: CywareIntelExchange,
    ) -> None:
        cyware.bulk_lookup_response = MOCK_BULK_LOOKUP
        cyware.create_task_response = MOCK_CREATE_TASK
        cyware.get_user_by_email_response = MOCK_GET_USER_BY_EMAIL
        success_output_msg_prefix = "Successfully created tasks"

        create_task_for_iocs.main()

        assert len(script_session.request_history) >= 1
        assert success_output_msg_prefix in action_output.results.output_message
        assert action_output.results.result_value is True
        assert action_output.results.execution_state.value == 0

    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        parameters={
            "Text": "Investigate this IOC for potential threats",
            "Priority": "medium",
            "Status": "in_progress",
            "Deadline": "3",
        },
        entities=DEFAULT_ENTITIES,
    )
    def test_create_task_for_iocs_success_without_assignee(
        self,
        script_session: CywareSession,
        action_output: MockActionOutput,
        cyware: CywareIntelExchange,
    ) -> None:
        cyware.bulk_lookup_response = MOCK_BULK_LOOKUP
        cyware.create_task_response = MOCK_CREATE_TASK
        success_output_msg_prefix = "Successfully created tasks"

        create_task_for_iocs.main()

        assert len(script_session.request_history) >= 1
        assert success_output_msg_prefix in action_output.results.output_message
        assert action_output.results.result_value is True
        assert action_output.results.execution_state.value == 0

    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        parameters=DEFAULT_PARAMETERS,
        entities=[],
    )
    def test_create_task_for_iocs_no_entities(
        self,
        script_session: CywareSession,
        action_output: MockActionOutput,
        cyware: CywareIntelExchange,
    ) -> None:
        create_task_for_iocs.main()

        assert "No entities found to process" in action_output.results.output_message
        assert action_output.results.result_value is True
        assert action_output.results.execution_state.value == 0

    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        parameters=DEFAULT_PARAMETERS,
        entities=DEFAULT_ENTITIES,
    )
    def test_create_task_for_iocs_no_valid_iocs(
        self,
        script_session: CywareSession,
        action_output: MockActionOutput,
        cyware: CywareIntelExchange,
    ) -> None:
        cyware.bulk_lookup_response = {"results": [], "total": 0}
        error_msg = "None of the provided indicators were found"

        create_task_for_iocs.main()

        assert error_msg in action_output.results.output_message
        assert action_output.results.result_value is True
        assert action_output.results.execution_state.value == 0

    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        parameters={
            "Text": "A" * 2001,
            "Priority": "high",
            "Status": "not_started",
            "Deadline": "7",
        },
        entities=DEFAULT_ENTITIES,
    )
    def test_create_task_for_iocs_text_too_long(
        self,
        script_session: CywareSession,
        action_output: MockActionOutput,
        cyware: CywareIntelExchange,
    ) -> None:
        create_task_for_iocs.main()

        assert "Text must not exceed 2000 characters" in action_output.results.output_message
        assert action_output.results.result_value is False
        assert action_output.results.execution_state.value == 2

    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        parameters={
            "Text": "Investigate this IOC",
            "Priority": "high",
            "Status": "not_started",
            "Deadline": "7",
            "Assignee Email ID": "nonexistent@example.com",
        },
        entities=DEFAULT_ENTITIES,
    )
    def test_create_task_for_iocs_user_not_found(
        self,
        script_session: CywareSession,
        action_output: MockActionOutput,
        cyware: CywareIntelExchange,
    ) -> None:
        cyware.bulk_lookup_response = MOCK_BULK_LOOKUP
        cyware.get_user_by_email_response = {"count": 0, "results": []}
        error_msg = "not found in Cyware Intel Exchange"

        create_task_for_iocs.main()

        assert error_msg in action_output.results.output_message
        assert action_output.results.result_value is False
        assert action_output.results.execution_state.value == 2

    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        parameters={
            "Text": "Investigate this IOC",
            "Priority": "critical",
            "Status": "completed",
            "Deadline": "30",
        },
        entities=[
            {"identifier": "malicious.com", "entity_type": "HOSTNAME", "additional_properties": {}},
        ],
    )
    def test_create_task_for_iocs_single_entity(
        self,
        script_session: CywareSession,
        action_output: MockActionOutput,
        cyware: CywareIntelExchange,
    ) -> None:
        cyware.bulk_lookup_response = MOCK_BULK_LOOKUP
        cyware.create_task_response = MOCK_CREATE_TASK
        success_output_msg_prefix = "Successfully created tasks"

        create_task_for_iocs.main()

        assert success_output_msg_prefix in action_output.results.output_message
        assert action_output.results.result_value is True
        assert action_output.results.execution_state.value == 0
