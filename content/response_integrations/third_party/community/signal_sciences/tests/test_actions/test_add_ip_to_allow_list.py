from __future__ import annotations

from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata
from TIPCommon.base.action import ExecutionState

from signal_sciences.actions import AddIpToAllowList
from signal_sciences.tests.common import CONFIG_PATH
from signal_sciences.tests.core.product import SignalSciencesProduct
from signal_sciences.tests.core.session import SignalSciencesSession


DEFAULT_PARAMETERS = {
    "Site Name": "test_site",
    "Note": "Test Reason",
    "IP Address": "1.1.1.1"
}


class TestAddIpToAllowList:
    @set_metadata(integration_config_file_path=CONFIG_PATH, parameters=DEFAULT_PARAMETERS)
    def test_add_ip_success(
        self,
        script_session: SignalSciencesSession,
        action_output: MockActionOutput,
        signal_sciences: SignalSciencesProduct,
    ) -> None:
        # Act
        AddIpToAllowList.main()

        # Assert
        assert len(script_session.request_history) == 1
        request = script_session.request_history[0].request
        assert request.method.value == "PUT"
        assert request.url.path.endswith("/whitelist")
        
        payload = script_session.request_history[0].request.kwargs.get("json")
        assert payload is not None
        assert payload["source"] == "1.1.1.1"
        assert payload["note"] == "Test Reason"

        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert "Successfully added IPs to allow list" in action_output.results.output_message
