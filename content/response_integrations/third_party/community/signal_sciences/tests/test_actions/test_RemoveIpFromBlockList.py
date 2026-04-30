from __future__ import annotations

from integration_testing.common import create_entity
from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata
from TIPCommon.base.action import ExecutionState
from TIPCommon.base.action.data_models import EntityTypesEnum

from signal_sciences.actions import RemoveIpFromBlockList
from signal_sciences.tests.common import CONFIG_PATH
from signal_sciences.tests.core.product import SignalSciences
from signal_sciences.tests.core.session import SignalSciencesSession


class TestRemoveIpFromBlockList:
    @set_metadata(
        parameters={
            "Site Name": "test-site",
            "IP Address": "1.2.3.5",
        },
        integration_config_file_path=CONFIG_PATH,
    )
    def test_remove_ip_from_block_list_success(
        self,
        script_session: SignalSciencesSession,
        action_output: MockActionOutput,
        signal_sciences: SignalSciences,
    ) -> None:
        # Arrange
        corp_name = "test-corp"
        site_name = "test-site"
        signal_sciences.add_corp(corp_name, {"name": corp_name})
        signal_sciences.add_ip_to_blocklist(corp_name, site_name, "1.2.3.5", "Note")

        # Act
        RemoveIpFromBlockList.main()

        # Assert
        assert any(r.request.method.value == "DELETE" for r in script_session.request_history)
        assert "Successfully removed" in action_output.results.output_message
        assert "1.2.3.5" in action_output.results.output_message
        assert action_output.results.result_value is True
        assert action_output.results.execution_state == ExecutionState.COMPLETED

    @set_metadata(
        parameters={
            "Site Name": "test-site",
            "IP Address": "1.2.3.5",
        },
        integration_config_file_path=CONFIG_PATH,
    )
    def test_remove_ip_from_block_list_not_found(
        self,
        script_session: SignalSciencesSession,
        action_output: MockActionOutput,
        signal_sciences: SignalSciences,
    ) -> None:
        # Arrange
        signal_sciences.add_corp("test-corp", {"name": "test-corp"})

        # Act
        RemoveIpFromBlockList.main()

        # Assert
        assert not any(r.request.method == "DELETE" for r in script_session.request_history)
        assert "Successfully removed" in action_output.results.output_message
        assert "1.2.3.5" in action_output.results.output_message
        assert action_output.results.result_value is True
        assert action_output.results.execution_state == ExecutionState.COMPLETED

    @set_metadata(
        parameters={
            "Site Name": "non-existent-site",
            "IP Address": "1.2.3.5",
        },
        integration_config_file_path=CONFIG_PATH,
    )
    def test_remove_ip_from_block_list_site_not_found(
        self,
        script_session: SignalSciencesSession,
        action_output: MockActionOutput,
        signal_sciences: SignalSciences,
    ) -> None:
        # Arrange
        signal_sciences.add_corp("test-corp", {"name": "test-corp"})

        # Act
        RemoveIpFromBlockList.main()

        # Assert
        assert "Reason: Site non-existent-site not found." in action_output.results.output_message
        assert action_output.results.result_value is False
        assert action_output.results.execution_state == ExecutionState.FAILED

    @set_metadata(
        parameters={
            "Site Name": "test-site",
            "IP Address": "1.2.3.5, 5.6.7.9",
        },
        integration_config_file_path=CONFIG_PATH,
    )
    def test_remove_ip_from_block_list_partial_success(
        self,
        script_session: SignalSciencesSession,
        action_output: MockActionOutput,
        signal_sciences: SignalSciences,
    ) -> None:
        # Arrange
        corp_name = "test-corp"
        site_name = "test-site"
        signal_sciences.add_corp(corp_name, {"name": corp_name})
        signal_sciences.add_ip_to_blocklist(corp_name, site_name, "1.2.3.5", "Note")

        # Act
        RemoveIpFromBlockList.main()

        # Assert
        assert "Successfully removed" in action_output.results.output_message
        assert action_output.results.result_value is True
        assert action_output.results.execution_state == ExecutionState.COMPLETED

    @set_metadata(
        parameters={
            "Site Name": "test-site",
            "IP Address": "1.2.3.5",
        },
        entities=[create_entity("5.6.7.9", EntityTypesEnum.ADDRESS)],
        integration_config_file_path=CONFIG_PATH,
    )
    def test_remove_ip_from_block_list_with_entities(
        self,
        script_session: SignalSciencesSession,
        action_output: MockActionOutput,
        signal_sciences: SignalSciences,
    ) -> None:
        # Arrange
        corp_name = "test-corp"
        site_name = "test-site"
        signal_sciences.add_corp(corp_name, {"name": corp_name})
        signal_sciences.add_ip_to_blocklist(corp_name, site_name, "1.2.3.5", "Note")
        signal_sciences.add_ip_to_blocklist(corp_name, site_name, "5.6.7.9", "Note")

        # Act
        RemoveIpFromBlockList.main()

        # Assert
        delete_requests = [
            r for r in script_session.request_history if r.request.method.value == "DELETE"
        ]
        assert len(delete_requests) == 2
        assert "1.2.3.5" in action_output.results.output_message
        assert "5.6.7.9" in action_output.results.output_message
        assert action_output.results.result_value is True
