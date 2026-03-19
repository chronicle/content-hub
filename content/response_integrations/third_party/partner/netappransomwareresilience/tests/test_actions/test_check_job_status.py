from __future__ import annotations

from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata

from netappransomwareresilience.actions import check_job_status
from netappransomwareresilience.tests.common import CONFIG_PATH, MOCK_CHECK_JOB_STATUS_RESPONSE
from netappransomwareresilience.tests.core.product import RansomwareResilience
from netappransomwareresilience.tests.core.session import RRSSession

DEFAULT_PARAMETERS = {
    "Source": "rps-agent",
    "Agent ID": "EAvI3XQqTeYvuiKeIlpBNPPl6n1ZxnAAclients",
    "Job ID": "f9b2f6028fdbc6b386ce40f00c887e1b::job-1",
}


class TestCheckJobStatus:
    @set_metadata(integration_config_file_path=CONFIG_PATH, parameters=DEFAULT_PARAMETERS)
    def test_check_job_status_success(
        self,
        script_session: RRSSession,
        action_output: MockActionOutput,
        rrs: RansomwareResilience,
    ) -> None:
        """Test that Check Job Status action succeeds."""
        rrs.check_job_status_response = MOCK_CHECK_JOB_STATUS_RESPONSE
        success_output_msg = "Successfully retrieved job status"

        check_job_status.main()

        assert len(script_session.request_history) >= 1
        job_requests = [
            req for req in script_session.request_history if "job/status" in req.request.url.path
        ]
        assert len(job_requests) >= 1

        assert action_output.results.output_message == success_output_msg
        assert action_output.results.result_value is True
        assert action_output.results.execution_state.value == 0

    @set_metadata(integration_config_file_path=CONFIG_PATH, parameters=DEFAULT_PARAMETERS)
    def test_check_job_status_api_error_500(
        self,
        script_session: RRSSession,
        action_output: MockActionOutput,
        rrs: RansomwareResilience,
    ) -> None:
        """Test that Check Job Status handles a 500 server error gracefully."""
        rrs.check_job_status_status_code = 500
        rrs.check_job_status_response = {"error": "Internal Server Error"}

        check_job_status.main()

        assert action_output.results.result_value is False
        assert action_output.results.execution_state.value == 2

    @set_metadata(integration_config_file_path=CONFIG_PATH, parameters=DEFAULT_PARAMETERS)
    def test_check_job_status_api_error_401(
        self,
        script_session: RRSSession,
        action_output: MockActionOutput,
        rrs: RansomwareResilience,
    ) -> None:
        """Test that Check Job Status handles a 401 unauthorized error gracefully."""
        rrs.check_job_status_status_code = 401
        rrs.check_job_status_response = {"error": "Unauthorized"}

        check_job_status.main()

        assert action_output.results.result_value is False
        assert action_output.results.execution_state.value == 2
