from __future__ import annotations

from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata
from TIPCommon.base.action import ExecutionState

from darkeye.actions import ping
from darkeye.tests.common import BREACH_HOUSE_ONLY_CONFIG, CONFIG, CONFIG_PATH, NO_KEY_CONFIG
from darkeye.tests.core.product import DarkEye
from darkeye.tests.core.session import DarkEyeSession


class TestPing:
    @set_metadata(integration_config_file_path=CONFIG_PATH)
    def test_ping_success(
        self,
        script_session: DarkEyeSession,
        action_output: MockActionOutput,
    ) -> None:
        ping.main()

        requests = [record.request for record in script_session.request_history]
        assert [request.url.path for request in requests] == ["/api/metadata/domain/example.com", "/api/v1/me"]
        assert [request.url.netloc for request in requests] == ["haveibeenransom.com", "breach.house"]
        assert requests[0].kwargs["headers"] == {"Authorization": f"Bearer {CONFIG['HaveIBeenRansom API Key']}"}
        assert requests[1].kwargs["headers"] == {"Authorization": f"Bearer {CONFIG['Breach House API Key']}"}
        assert all(request.kwargs["allow_redirects"] is False for request in requests)
        assert action_output.results.output_message == (
            "Successfully connected to the DarkEye server with the provided connection parameters! "
            "Checked: HaveIBeenRansom, Breach House."
        )
        assert action_output.results.execution_state == ExecutionState.COMPLETED

    @set_metadata(integration_config=BREACH_HOUSE_ONLY_CONFIG)
    def test_ping_checks_only_configured_products(
        self,
        script_session: DarkEyeSession,
        action_output: MockActionOutput,
    ) -> None:
        ping.main()

        assert [record.request.url.path for record in script_session.request_history] == ["/api/v1/me"]
        assert action_output.results.output_message.endswith("Checked: Breach House.")
        assert action_output.results.execution_state == ExecutionState.COMPLETED

    @set_metadata(integration_config_file_path=CONFIG_PATH)
    def test_ping_failure(
        self,
        action_output: MockActionOutput,
        darkeye: DarkEye,
    ) -> None:
        darkeye.fail("HaveIBeenRansom", 401)

        ping.main()

        message: str = action_output.results.output_message
        assert message.startswith("Failed to connect to the DarkEye server!")
        assert "HaveIBeenRansom: authentication failed" in message
        assert CONFIG["HaveIBeenRansom API Key"] not in message
        assert action_output.results.execution_state == ExecutionState.FAILED

    @set_metadata(integration_config=NO_KEY_CONFIG)
    def test_ping_without_keys_fails(
        self,
        script_session: DarkEyeSession,
        action_output: MockActionOutput,
    ) -> None:
        ping.main()

        assert not script_session.request_history
        assert "Configure the HaveIBeenRansom API Key, the Breach House API Key or both." in (
            action_output.results.output_message
        )
        assert action_output.results.execution_state == ExecutionState.FAILED
