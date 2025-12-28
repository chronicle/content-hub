from __future__ import annotations

from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata
from TIPCommon.base.action import ExecutionState

from ...actions import SendLocation
from ..common import CONFIG_PATH
from ..core.product import Telegram
from ..core.session import TelegramSession


class TestSendLocation:
    CHAT_ID = "123456789"
    LATITUDE = "34.0522"
    LONGITUDE = "-118.2437"

    @set_metadata(
        parameters={"Chat ID": CHAT_ID, "Latitude": LATITUDE, "Longitude": LONGITUDE},
        integration_config_file_path=CONFIG_PATH,
    )
    def test_send_location_success(
        self,
        script_session: TelegramSession,
        action_output: MockActionOutput,
        telegram: Telegram,
    ) -> None:
        expected_send_location_response = {
            "ok": True,
            "result": {
                "chat_id": self.CHAT_ID,
                "latitude": self.LATITUDE,
                "longitude": self.LONGITUDE,
            },
        }
        telegram.set_send_location_response(expected_send_location_response)

        SendLocation.main()

        assert len(script_session.request_history) == 1
        request = script_session.request_history[0].request
        assert request.url.path.endswith("/sendLocation")
        assert request.kwargs["params"] == {
            "chat_id": self.CHAT_ID,
            "latitude": self.LATITUDE,
            "longitude": self.LONGITUDE,
        }

        assert (
            action_output.results.output_message == "The location was sent successfully"
        )
        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert (
            action_output.results.json_output.json_result
            == expected_send_location_response
        )

    @set_metadata(
        parameters={"Chat ID": CHAT_ID, "Latitude": LATITUDE, "Longitude": LONGITUDE},
        integration_config_file_path=CONFIG_PATH,
    )
    def test_send_location_failure(
        self,
        script_session: TelegramSession,
        action_output: MockActionOutput,
        telegram: Telegram,
    ) -> None:
        with telegram.fail_requests():
            SendLocation.main()

        assert len(script_session.request_history) == 1
        request = script_session.request_history[0].request
        assert request.url.path.endswith("/sendLocation")
        assert request.kwargs["params"] == {
            "chat_id": self.CHAT_ID,
            "latitude": self.LATITUDE,
            "longitude": self.LONGITUDE,
        }

        assert (
            action_output.results.output_message
            == "Could not sent location. Error: b'Mock API failure'"
        )
        assert action_output.results.execution_state == ExecutionState.FAILED
