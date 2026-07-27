from __future__ import annotations

from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata
from TIPCommon.base.action import ExecutionState

from ...actions import ListThreats
from ..common import CONFIG_PATH
from ..core.product import Abnormal
from ..core.session import AbnormalSession


class TestListThreats:
    @set_metadata(
        parameters={"Page Size": "100", "Page Number": "1"},
        integration_config_file_path=CONFIG_PATH,
    )
    def test_list_threats_success(
        self,
        script_session: AbnormalSession,
        action_output: MockActionOutput,
        abnormal: Abnormal,
    ) -> None:
        threat_payload = {
            "threats": [
                {
                    "threatId": "abc123",
                    "subject": "Phishing Attempt",
                    "attackType": "Credential Phishing",
                }
            ],
            "total": 1,
        }
        abnormal.set_threats_list_response(threat_payload)

        ListThreats.main()

        assert len(script_session.request_history) == 1
        request = script_session.request_history[0].request
        assert request.url.path.endswith("/v1/threats")
        assert action_output.results.execution_state == ExecutionState.COMPLETED
