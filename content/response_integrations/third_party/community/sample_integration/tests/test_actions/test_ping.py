from __future__ import annotations

import datetime

from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata
from TIPCommon.base.action import ExecutionState

from sample_integration.actions import ping
from sample_integration.tests.common import CONFIG_PATH, MOCK_RATES_DEFAULT
from sample_integration.tests.core.product import VatComply
from sample_integration.tests.core.session import VatComplySession


class TestPing:
    @set_metadata(integration_config_file_path=CONFIG_PATH)
    def test_ping_success(
        self,
        script_session: VatComplySession,
        action_output: MockActionOutput,
        vatcomply: VatComply,
    ) -> None:
        MOCK_RATES_DEFAULT["date"]: str = datetime.date.today().isoformat()
        vatcomply.set_rates(MOCK_RATES_DEFAULT)
        success_output_msg = (
            "Successfully connected to the API Service server with "
            "the provided connection parameters!"
        )

        ping.main()

        assert len(script_session.request_history) == 1
        request = script_session.request_history[0].request
        assert request.url.path.endswith("/rates")

        assert action_output.results.output_message == success_output_msg
        assert action_output.results.execution_state == ExecutionState.COMPLETED
