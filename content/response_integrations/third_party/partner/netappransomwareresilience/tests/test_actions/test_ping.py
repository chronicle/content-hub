from __future__ import annotations

from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata

from netappransomwareresilience.actions import ping
from netappransomwareresilience.tests.common import CONFIG_PATH
from netappransomwareresilience.tests.core.product import RansomwareResilience
from netappransomwareresilience.tests.core.session import RRSSession


class TestPing:
    @set_metadata(integration_config_file_path=CONFIG_PATH)
    def test_ping_success(
        self,
        script_session: RRSSession,
        action_output: MockActionOutput,
        rrs: RansomwareResilience,
    ) -> None:
        """Test that Ping action succeeds with valid token."""
        success_output_msg = "Successfully connected to Ransomware Resilience server!"

        ping.main()

        assert len(script_session.request_history) >= 1
        assert action_output.results.output_message == success_output_msg
        assert action_output.results.result_value is True
        assert action_output.results.execution_state.value == 0

    @set_metadata(integration_config_file_path=CONFIG_PATH)
    def test_ping_auth_failure(
        self,
        script_session: RRSSession,
        action_output: MockActionOutput,
        rrs: RansomwareResilience,
    ) -> None:
        """Test that Ping handles authentication failure gracefully."""
        rrs.token_status_code = 401
        rrs.token_response = {"error": "invalid_client"}

        ping.main()

        assert action_output.results.result_value is False
        assert action_output.results.execution_state.value == 2
