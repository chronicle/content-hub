from __future__ import annotations

from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata
from TIPCommon.base.action.data_models import ExecutionState

from signal_sciences.actions import ListSites
from signal_sciences.tests.common import CONFIG_PATH, SITES_DATA
from signal_sciences.tests.core.product import SignalSciences
from signal_sciences.tests.core.session import SignalSciencesSession


class TestListSites:
    @set_metadata(
        parameters={"Max Sites To Return": 50},
        integration_config_file_path=CONFIG_PATH,
    )
    def test_list_sites_success(
        self,
        script_session: SignalSciencesSession,
        action_output: MockActionOutput,
        signal_sciences: SignalSciences,
    ) -> None:
        # Arrange
        corp_name = "test-corp"
        for site in SITES_DATA:
            signal_sciences.add_site(corp_name, site)

        success_output_msg = (
            "Successfully fetched information about the following sites in Signal Sciences:\nsite1"
        )

        # Act
        ListSites.main()

        # Assert
        assert len(script_session.request_history) >= 1
        request = script_session.request_history[0].request
        assert request.method.value == "GET"
        assert request.url.path.endswith("/corps/test-corp/sites")

        assert success_output_msg in action_output.results.output_message
        assert action_output.results.result_value is True
        assert action_output.results.json_output.json_result == SITES_DATA

    @set_metadata(
        parameters={"Max Sites To Return": 0},
        integration_config_file_path=CONFIG_PATH,
    )
    def test_list_sites_unlimited(
        self,
        script_session: SignalSciencesSession,
        action_output: MockActionOutput,
        signal_sciences: SignalSciences,
    ) -> None:
        # Arrange
        corp_name = "test-corp"
        for i in range(15):
            signal_sciences.add_site(corp_name, {"name": f"site{i}", "displayName": f"Site {i}"})

        # Act
        ListSites.main()

        # Assert
        assert action_output.results.execution_state == ExecutionState.COMPLETED
        # The script should have gathered all 15 sites
        assert len(action_output.results.json_output.json_result) == 15
        for i in range(15):
            assert action_output.results.json_output.json_result[i]["name"] == f"site{i}"

    @set_metadata(
        parameters={"Max Sites To Return": None},
        integration_config_file_path=CONFIG_PATH,
    )
    def test_list_sites_empty_param(
        self,
        script_session: SignalSciencesSession,
        action_output: MockActionOutput,
        signal_sciences: SignalSciences,
    ) -> None:
        # Arrange
        corp_name = "test-corp"
        signal_sciences.add_site(corp_name, {"name": "site1"})

        # Act
        ListSites.main()
        expected_json = [{"name": "site1"}]  # Since we only added one site in this test case

        # Assert
        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert action_output.results.json_output.json_result == expected_json
