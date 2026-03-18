from __future__ import annotations

from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata
from TIPCommon.base.action import ExecutionState

from signal_sciences.actions import RemoveIpFromBlockList
from signal_sciences.tests.common import CONFIG_PATH
from signal_sciences.tests.core.product import SignalSciencesProduct
from signal_sciences.tests.core.session import SignalSciencesSession


DEFAULT_PARAMETERS = {
    "Site Name": "test_site",
    "IP Address": "1.1.1.1"
}


class TestRemoveIpFromBlockList:
    @set_metadata(integration_config_file_path=CONFIG_PATH, parameters=DEFAULT_PARAMETERS)
    def test_remove_ip_success(
        self,
        script_session: SignalSciencesSession,
        action_output: MockActionOutput,
        signal_sciences: SignalSciencesProduct,
    ) -> None:
        # Arrange
        signal_sciences.add_blacklist_item("test_site", {"source": "1.1.1.1", "id": "bl_1"})

        # Act
        RemoveIpFromBlockList.main()

        # Assert
        assert len(script_session.request_history) == 2
        
        get_request = script_session.request_history[0].request
        assert get_request.method.value == "GET"
        assert get_request.url.path.endswith("/blacklist")

        delete_request = script_session.request_history[1].request
        assert delete_request.method.value == "DELETE"
        assert delete_request.url.path.endswith("/blacklist/bl_1")

        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert "Successfully removed" in action_output.results.output_message
