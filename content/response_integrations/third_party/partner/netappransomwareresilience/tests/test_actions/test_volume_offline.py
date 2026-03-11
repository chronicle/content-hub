from __future__ import annotations

from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata

from netappransomwareresilience.actions import volume_offline
from netappransomwareresilience.tests.common import CONFIG_PATH, MOCK_VOLUME_OFFLINE_RESPONSE
from netappransomwareresilience.tests.core.product import RansomwareResilience
from netappransomwareresilience.tests.core.session import RRSSession

DEFAULT_PARAMETERS = {
    "Volume ID": "4cb4af41-0432-11f1-80b2-d5190c5fee24",
    "Agent ID": "EAvI3XQqTeYvuiKeIlpBNPPl6n1ZxnAAclients",
    "System ID": "VsaWorkingEnvironment-A2hoS8xl",
}


class TestVolumeOffline:
    @set_metadata(integration_config_file_path=CONFIG_PATH, parameters=DEFAULT_PARAMETERS)
    def test_volume_offline_success(
        self,
        script_session: RRSSession,
        action_output: MockActionOutput,
        rrs: RansomwareResilience,
    ) -> None:
        """Test that Volume Offline action succeeds."""
        rrs.volume_offline_response = MOCK_VOLUME_OFFLINE_RESPONSE
        success_output_msg = "Successfully took volume offline"

        volume_offline.main()

        assert len(script_session.request_history) >= 1
        offline_requests = [
            req
            for req in script_session.request_history
            if "storage/take-volume-offline" in req.request.url.path
        ]
        assert len(offline_requests) >= 1

        assert action_output.results.output_message == success_output_msg
        assert action_output.results.result_value is True
        assert action_output.results.execution_state.value == 0

    @set_metadata(integration_config_file_path=CONFIG_PATH, parameters=DEFAULT_PARAMETERS)
    def test_volume_offline_api_error_500(
        self,
        script_session: RRSSession,
        action_output: MockActionOutput,
        rrs: RansomwareResilience,
    ) -> None:
        """Test that Volume Offline handles a 500 server error gracefully."""
        rrs.volume_offline_status_code = 500
        rrs.volume_offline_response = {"error": "Internal Server Error"}

        volume_offline.main()

        assert action_output.results.result_value is False
        assert action_output.results.execution_state.value == 2

    @set_metadata(integration_config_file_path=CONFIG_PATH, parameters=DEFAULT_PARAMETERS)
    def test_volume_offline_api_error_401(
        self,
        script_session: RRSSession,
        action_output: MockActionOutput,
        rrs: RansomwareResilience,
    ) -> None:
        """Test that Volume Offline handles a 401 unauthorized error gracefully."""
        rrs.volume_offline_status_code = 401
        rrs.volume_offline_response = {"error": "Unauthorized"}

        volume_offline.main()

        assert action_output.results.result_value is False
        assert action_output.results.execution_state.value == 2
