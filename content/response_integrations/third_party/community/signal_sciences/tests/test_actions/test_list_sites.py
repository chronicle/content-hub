from __future__ import annotations

from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata
from TIPCommon.base.action import ExecutionState

from signal_sciences.actions import ListSites
from signal_sciences.tests.common import CONFIG_PATH
from signal_sciences.tests.core.product import SignalSciencesProduct
from signal_sciences.tests.core.session import SignalSciencesSession


class TestListSites:
    @set_metadata(integration_config_file_path=CONFIG_PATH)
    def test_list_sites_success(
        self,
        script_session: SignalSciencesSession,
        action_output: MockActionOutput,
        signal_sciences: SignalSciencesProduct,
    ) -> None:
        # Arrange
        signal_sciences.add_site({"name": "site_1", "displayName": "Site 1"})
        signal_sciences.add_site({"name": "site_2", "displayName": "Site 2"})

        # Act
        ListSites.main()

        # Assert
        assert len(script_session.request_history) == 1
        request = script_session.request_history[0].request
        assert request.method.value == "GET"
        assert request.url.path.endswith("/sites")

        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert "Successfully found 2 sites" in action_output.results.output_message
