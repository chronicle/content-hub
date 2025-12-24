from __future__ import annotations

from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata
from TIPCommon.base.action import ExecutionState

from ...actions import SendDocument
from ..common import CONFIG_PATH
from ..core.product import Telegram
from ..core.session import TelegramSession


class TestSendDocument:
    CHAT_ID = "123456789"
    DOCUMENT_URL = "http://example.com/document.pdf"

    @set_metadata(
        parameters={"Chat ID": CHAT_ID, "Document URL": DOCUMENT_URL},
        integration_config_file_path=CONFIG_PATH,
    )
    def test_send_document_success(
        self,
        script_session: TelegramSession,
        action_output: MockActionOutput,
        telegram: Telegram,
    ) -> None:
        expected_send_doc_response = {
            "ok": True,
            "result": {
                "chat_id": self.CHAT_ID,
                "document_url": self.DOCUMENT_URL,
                "file_id": "test_file_id",
            },
        }
        telegram.set_send_doc_response(expected_send_doc_response)

        SendDocument.main()

        assert len(script_session.request_history) == 1
        request = script_session.request_history[0].request
        assert request.url.path.endswith("/sendDocument")
        assert request.kwargs["params"] == {
            "chat_id": self.CHAT_ID,
            "document": self.DOCUMENT_URL,
        }

        assert (
            action_output.results.output_message == "The document was sent successfully"
        )
        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert (
            action_output.results.json_output.json_result == expected_send_doc_response
        )
