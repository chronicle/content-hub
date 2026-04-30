from __future__ import annotations

from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata

from rubrik_security_cloud.actions import ioc_scan_results
from rubrik_security_cloud.tests.common import CONFIG_PATH, MOCK_IOC_SCAN_RESULTS
from rubrik_security_cloud.tests.core.product import RubrikSecurityCloud
from rubrik_security_cloud.tests.core.session import RubrikSession

DEFAULT_PARAMETERS = {
    "Hunt ID": "hunt-123",
}


class TestIOCScanResults:
    @set_metadata(integration_config_file_path=CONFIG_PATH, parameters=DEFAULT_PARAMETERS)
    def test_ioc_scan_results_success(
        self,
        script_session: RubrikSession,
        action_output: MockActionOutput,
        rubrik: RubrikSecurityCloud,
    ) -> None:
        rubrik.ioc_scan_results_response = MOCK_IOC_SCAN_RESULTS
        success_output_msg = "Successfully retrieved IOC Scan Results for Hunt ID: hunt-123"

        ioc_scan_results.main()

        assert len(script_session.request_history) >= 1
        graphql_requests = [
            req
            for req in script_session.request_history
            if req.request.url.path.endswith("/api/graphql")
        ]
        assert len(graphql_requests) >= 1

        assert action_output.results.output_message == success_output_msg
        assert action_output.results.result_value is True
        assert action_output.results.execution_state.value == 0
