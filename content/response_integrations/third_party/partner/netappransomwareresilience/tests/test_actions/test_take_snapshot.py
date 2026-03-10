from __future__ import annotations

from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata

from netappransomwareresilience.actions import Take_Snapshot
from netappransomwareresilience.tests.common import CONFIG_PATH, MOCK_TAKE_SNAPSHOT_RESPONSE
from netappransomwareresilience.tests.core.product import RansomwareResilience
from netappransomwareresilience.tests.core.session import RRSSession

DEFAULT_PARAMETERS = {
    "Volume ID": "4cb4af41-0432-11f1-80b2-d5190c5fee24",
    "Agent ID": "EAvI3XQqTeYvuiKeIlpBNPPl6n1ZxnAAclients",
    "System ID": "VsaWorkingEnvironment-A2hoS8xl",
}


class TestTakeSnapshot:
    @set_metadata(integration_config_file_path=CONFIG_PATH, parameters=DEFAULT_PARAMETERS)
    def test_take_snapshot_success(
        self,
        script_session: RRSSession,
        action_output: MockActionOutput,
        rrs: RansomwareResilience,
    ) -> None:
        """Test that Take Snapshot action succeeds."""
        rrs.take_snapshot_response = MOCK_TAKE_SNAPSHOT_RESPONSE
        success_output_msg = "Successfully triggered snapshot creation"

        Take_Snapshot.main()

        assert len(script_session.request_history) >= 1
        snapshot_requests = [
            req
            for req in script_session.request_history
            if "storage/take-snapshot" in req.request.url.path
        ]
        assert len(snapshot_requests) >= 1

        assert action_output.results.output_message == success_output_msg
        assert action_output.results.result_value is True
        assert action_output.results.execution_state.value == 0
