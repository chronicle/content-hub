from __future__ import annotations

from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata

from netappransomwareresilience.actions import block_user
from netappransomwareresilience.tests.common import CONFIG_PATH, MOCK_BLOCK_USER_RESPONSE
from netappransomwareresilience.tests.core.product import RansomwareResilience
from netappransomwareresilience.tests.core.session import RRSSession

DEFAULT_PARAMETERS = {
    "User ID": "user123456789",
    "User IPs": "192.168.1.100, 192.168.1.101",
    "Duration": "permanent",
}


class TestBlockUser:
    @set_metadata(integration_config_file_path=CONFIG_PATH, parameters=DEFAULT_PARAMETERS)
    def test_block_user_success(
        self,
        script_session: RRSSession,
        action_output: MockActionOutput,
        rrs: RansomwareResilience,
    ) -> None:
        """Test that Block User action succeeds."""
        rrs.block_user_response = MOCK_BLOCK_USER_RESPONSE
        success_output_msg = f"Successfully blocked user on the following entities using NetApp Ransomware Resilience: {DEFAULT_PARAMETERS['User ID']}"

        block_user.main()

        assert len(script_session.request_history) >= 1
        block_requests = [req for req in script_session.request_history if "users/block-user" in req.request.url.path]
        assert len(block_requests) >= 1

        assert action_output.results.output_message == success_output_msg
        assert action_output.results.result_value is True
        assert action_output.results.execution_state.value == 0

    @set_metadata(integration_config_file_path=CONFIG_PATH, parameters=DEFAULT_PARAMETERS)
    def test_block_user_api_error_500(
        self,
        script_session: RRSSession,
        action_output: MockActionOutput,
        rrs: RansomwareResilience,
    ) -> None:
        """Test that Block User handles a 500 server error gracefully."""
        rrs.block_user_status_code = 500
        rrs.block_user_response = {"error": "Internal Server Error"}

        block_user.main()

        assert action_output.results.result_value is False
        assert action_output.results.execution_state.value == 2

    @set_metadata(integration_config_file_path=CONFIG_PATH, parameters=DEFAULT_PARAMETERS)
    def test_block_user_api_error_401(
        self,
        script_session: RRSSession,
        action_output: MockActionOutput,
        rrs: RansomwareResilience,
    ) -> None:
        """Test that Block User handles a 401 unauthorized error gracefully."""
        rrs.block_user_status_code = 401
        rrs.block_user_response = {"error": "Unauthorized"}

        block_user.main()

        assert action_output.results.result_value is False
        assert action_output.results.execution_state.value == 2

    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        parameters={
            "User ID": "",
            "User IPs": "192.168.1.100",
            "Duration": "1",
        },
    )
    def test_block_user_without_user_id(
        self,
        script_session: RRSSession,
        action_output: MockActionOutput,
        rrs: RansomwareResilience,
    ) -> None:
        """Test that Block User fails when User ID is empty (mandatory field)."""
        rrs.block_user_response = MOCK_BLOCK_USER_RESPONSE
        expected_output_msg = 'Error executing action "Block User". Reason: Missing mandatory parameter User ID'

        block_user.main()

        assert action_output.results.output_message == expected_output_msg
        assert action_output.results.result_value is False
        assert action_output.results.execution_state.value == 2

    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        parameters={
            "User ID": "user123456789",
            "User IPs": "",
            "Duration": "24",
        },
    )
    def test_block_user_without_user_ips(
        self,
        script_session: RRSSession,
        action_output: MockActionOutput,
        rrs: RansomwareResilience,
    ) -> None:
        """Test that Block User succeeds without user IPs (optional for CIFS)."""
        rrs.block_user_response = MOCK_BLOCK_USER_RESPONSE
        success_output_msg = (
            "Successfully blocked user on the following entities using NetApp Ransomware Resilience: user123456789"
        )

        block_user.main()

        assert action_output.results.output_message == success_output_msg
        assert action_output.results.result_value is True
        assert action_output.results.execution_state.value == 0
