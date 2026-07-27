from __future__ import annotations

from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata
from TIPCommon.base.action import ExecutionState

from ...actions import GetThreat
from ..common import CONFIG_PATH
from ..core.product import Abnormal
from ..core.session import AbnormalSession


class TestGetThreat:
    THREAT_ID = "abc123"

    @set_metadata(
        parameters={"Threat ID": THREAT_ID},
        integration_config_file_path=CONFIG_PATH,
    )
    def test_get_threat_success(
        self,
        script_session: AbnormalSession,
        action_output: MockActionOutput,
        abnormal: Abnormal,
    ) -> None:
        threat_response = {
            "threatId": self.THREAT_ID,
            "subject": "Suspicious Email",
            "attackType": "Phishing",
            "messages": [],
        }
        abnormal.set_threat_response(threat_response)

        GetThreat.main()

        assert len(script_session.request_history) == 1
        request = script_session.request_history[0].request
        assert request.url.path == f"/v1/threats/{self.THREAT_ID}"
        assert action_output.results.execution_state == ExecutionState.COMPLETED

    @set_metadata(
        parameters={"Threat ID": THREAT_ID},
        integration_config_file_path=CONFIG_PATH,
    )
    def test_get_threat_failure(
        self,
        script_session: AbnormalSession,
        action_output: MockActionOutput,
        abnormal: Abnormal,
    ) -> None:
        with abnormal.fail_requests():
            GetThreat.main()

        assert action_output.results.execution_state == ExecutionState.FAILED
