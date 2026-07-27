from __future__ import annotations

from integration_testing.common import create_entity
from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata
from TIPCommon.base.action import ExecutionState
from TIPCommon.base.action.data_models import EntityTypesEnum

from signal_sciences.actions import AddIpToBlockList
from signal_sciences.tests.common import CONFIG_PATH
from signal_sciences.tests.core.product import SignalSciences
from signal_sciences.tests.core.session import SignalSciencesSession


class TestAddIpToBlockList:
    @set_metadata(
        parameters={
            "Site Name": "test-site",
            "IP Address": "1.2.3.5",
            "Note": "Test Note",
        },
        integration_config_file_path=CONFIG_PATH,
    )
    def test_add_ip_to_block_list_success(
        self,
        script_session: SignalSciencesSession,
        action_output: MockActionOutput,
        signal_sciences: SignalSciences,
    ) -> None:
        # Arrange
        signal_sciences.add_corp("test-corp", {"name": "test-corp"})

        # Act
        AddIpToBlockList.main()

        # Assert
        assert any(
            r.request.method.value == "PUT"
            and r.request.kwargs.get("json", {}).get("source") == "1.2.3.5"
            for r in script_session.request_history
        )
        assert "Successfully added" in action_output.results.output_message
        assert "1.2.3.5" in action_output.results.output_message
        assert action_output.results.result_value is True
        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert action_output.results.json_output.json_result == {
            "added_entities": ["1.2.3.5"],
            "failed_entities": [],
            "site_name": "test-site",
            "created_by": "test-user",
            "note": "Test Note",
            "created": "2024-12-16T15:13:40Z",
        }

    @set_metadata(
        parameters={
            "Site Name": "test-site",
            "IP Address": "1.2.3.5",
            "Note": "Test Note",
        },
        integration_config_file_path=CONFIG_PATH,
    )
    def test_add_ip_to_block_list_already_exists(
        self,
        script_session: SignalSciencesSession,
        action_output: MockActionOutput,
        signal_sciences: SignalSciences,
    ) -> None:
        # Arrange
        corp_name = "test-corp"
        site_name = "test-site"
        signal_sciences.add_corp(corp_name, {"name": corp_name})
        signal_sciences.add_ip_to_blocklist(corp_name, site_name, "1.2.3.5", "Existing Note")

        # Act
        AddIpToBlockList.main()

        # Assert
        assert not any(r.request.method == "PUT" for r in script_session.request_history)
        assert "Successfully added" in action_output.results.output_message
        assert "1.2.3.5" in action_output.results.output_message
        assert action_output.results.result_value is True
        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert action_output.results.json_output.json_result == {
            "added_entities": ["1.2.3.5"],
            "failed_entities": [],
            "site_name": "test-site",
            "created_by": "test-user",
            "note": "Existing Note",
            "created": "2024-12-16T15:13:40Z",
        }

    @set_metadata(
        parameters={
            "Site Name": "non-existent-site",
            "IP Address": "1.2.3.5",
            "Note": "Test Note",
        },
        integration_config_file_path=CONFIG_PATH,
    )
    def test_add_ip_to_block_list_site_not_found(
        self,
        script_session: SignalSciencesSession,
        action_output: MockActionOutput,
        signal_sciences: SignalSciences,
    ) -> None:
        # Arrange
        signal_sciences.add_corp("test-corp", {"name": "test-corp"})

        # Act
        AddIpToBlockList.main()

        # Assert
        assert "Reason: Site non-existent-site not found." in action_output.results.output_message
        assert action_output.results.result_value is False
        assert action_output.results.execution_state == ExecutionState.FAILED

    @set_metadata(
        parameters={
            "Site Name": "test-site",
            "IP Address": "1.2.3.5, 5.6.7.9",
            "Note": "Test Note",
        },
        integration_config_file_path=CONFIG_PATH,
    )
    def test_add_ip_to_block_list_partial_success(
        self,
        script_session: SignalSciencesSession,
        action_output: MockActionOutput,
        signal_sciences: SignalSciences,
    ) -> None:
        # Arrange
        signal_sciences.add_corp("test-corp", {"name": "test-corp"})

        # Act
        AddIpToBlockList.main()

        # Assert
        assert "Successfully added" in action_output.results.output_message
        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert len(action_output.results.json_output.json_result) >= 1

    @set_metadata(
        parameters={
            "Site Name": "test-site",
            "IP Address": "1.2.3.5",
            "Note": "Test Note",
        },
        entities=[create_entity("5.6.7.9", EntityTypesEnum.ADDRESS)],
        integration_config_file_path=CONFIG_PATH,
    )
    def test_add_ip_to_block_list_with_entities(
        self,
        script_session: SignalSciencesSession,
        action_output: MockActionOutput,
        signal_sciences: SignalSciences,
    ) -> None:
        # Arrange
        signal_sciences.add_corp("test-corp", {"name": "test-corp"})

        # Act
        AddIpToBlockList.main()

        # Assert
        put_requests = [
            r for r in script_session.request_history if r.request.method.value == "PUT"
        ]
        assert len(put_requests) == 2
        sources = [r.request.kwargs.get("json", {}).get("source") for r in put_requests]
        assert "1.2.3.5" in sources
        assert "5.6.7.9" in sources
        assert "1.2.3.5" in action_output.results.output_message
        assert "5.6.7.9" in action_output.results.output_message
        assert action_output.results.result_value is True
        # Verify both IPs are in the results
        results = action_output.results.json_output.json_result
        assert set(results["added_entities"]) == {"1.2.3.5", "5.6.7.9"}

        # Verify general fields
        assert results["note"] == "Test Note"
        assert results["created_by"] == "test-user"
