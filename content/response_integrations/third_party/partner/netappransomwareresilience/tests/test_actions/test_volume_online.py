from __future__ import annotations

from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata

from netappransomwareresilience.actions import volume_online
from netappransomwareresilience.tests.common import CONFIG_PATH, MOCK_VOLUME_ONLINE_RESPONSE
from netappransomwareresilience.tests.core.product import RansomwareResilience
from netappransomwareresilience.tests.core.session import RRSSession

DEFAULT_PARAMETERS = {
    "Volume ID": "4cb4af41-0432-11f1-80b2-d5190c5fee24",
    "Agent ID": "EAvI3XQqTeYvuiKeIlpBNPPl6n1ZxnAAclients",
    "System ID": "VsaWorkingEnvironment-A2hoS8xl",
}


class TestVolumeOnline:
    @set_metadata(integration_config_file_path=CONFIG_PATH, parameters=DEFAULT_PARAMETERS)
    def test_volume_online_success(
        self,
        script_session: RRSSession,
        action_output: MockActionOutput,
        rrs: RansomwareResilience,
    ) -> None:
        """Test that Volume Online action succeeds."""
        rrs.volume_online_response = MOCK_VOLUME_ONLINE_RESPONSE
        success_output_msg = (
            "Successfully brought volume online on the following entities using NetApp Ransomware Resilience: "
            f"{DEFAULT_PARAMETERS['Volume ID']}"
        )

        volume_online.main()

        assert len(script_session.request_history) >= 1
        online_requests = [
            req for req in script_session.request_history if "storage/take-volume-online" in req.request.url.path
        ]
        assert len(online_requests) >= 1

        assert action_output.results.output_message == success_output_msg
        assert action_output.results.result_value is True
        assert action_output.results.execution_state.value == 0

    @set_metadata(integration_config_file_path=CONFIG_PATH, parameters=DEFAULT_PARAMETERS)
    def test_volume_online_api_error_500(
        self,
        script_session: RRSSession,
        action_output: MockActionOutput,
        rrs: RansomwareResilience,
    ) -> None:
        """Test that Volume Online handles a 500 server error gracefully."""
        rrs.volume_online_status_code = 500
        rrs.volume_online_response = {"error": "Internal Server Error"}

        volume_online.main()

        assert action_output.results.result_value is False
        assert action_output.results.execution_state.value == 2

    @set_metadata(integration_config_file_path=CONFIG_PATH, parameters=DEFAULT_PARAMETERS)
    def test_volume_online_api_error_401(
        self,
        script_session: RRSSession,
        action_output: MockActionOutput,
        rrs: RansomwareResilience,
    ) -> None:
        """Test that Volume Online handles a 401 unauthorized error gracefully."""
        rrs.volume_online_status_code = 401
        rrs.volume_online_response = {"error": "Unauthorized"}

        volume_online.main()

        assert action_output.results.result_value is False
        assert action_output.results.execution_state.value == 2

    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        parameters={
            "Volume ID": "",
            "Agent ID": "EAvI3XQqTeYvuiKeIlpBNPPl6n1ZxnAAclients",
            "System ID": "VsaWorkingEnvironment-A2hoS8xl",
        },
    )
    def test_volume_online_without_volume_id(
        self,
        script_session: RRSSession,
        action_output: MockActionOutput,
        rrs: RansomwareResilience,
    ) -> None:
        """Test that Volume Online fails when Volume ID is empty (mandatory field)."""
        rrs.volume_online_response = MOCK_VOLUME_ONLINE_RESPONSE
        expected_output_msg = 'Error executing action "Volume Online". Reason: Missing mandatory parameter Volume ID'

        volume_online.main()

        assert action_output.results.output_message == expected_output_msg
        assert action_output.results.result_value is False
        assert action_output.results.execution_state.value == 2
