from __future__ import annotations

from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata

from netappransomwareresilience.actions import enrich_ip_address
from netappransomwareresilience.tests.common import CONFIG_PATH, MOCK_ENRICH_IP_RESPONSE
from netappransomwareresilience.tests.core.product import RansomwareResilience
from netappransomwareresilience.tests.core.session import RRSSession

DEFAULT_PARAMETERS = {
    "IP Address": "10.0.1.251",
}


class TestEnrichIPAddress:
    @set_metadata(integration_config_file_path=CONFIG_PATH, parameters=DEFAULT_PARAMETERS)
    def test_enrich_ip_success(
        self,
        script_session: RRSSession,
        action_output: MockActionOutput,
        rrs: RansomwareResilience,
    ) -> None:
        """Test that Enrich IP Address action succeeds."""
        rrs.enrich_ip_response = MOCK_ENRICH_IP_RESPONSE
        success_output_msg = "Successfully enriched IP - 10.0.1.251"

        enrich_ip_address.main()

        assert len(script_session.request_history) >= 1
        enrich_requests = [
            req
            for req in script_session.request_history
            if "enrich/ip-address" in req.request.url.path
        ]
        assert len(enrich_requests) >= 1

        assert action_output.results.output_message == success_output_msg
        assert action_output.results.result_value is True
        assert action_output.results.execution_state.value == 0

    @set_metadata(integration_config_file_path=CONFIG_PATH, parameters=DEFAULT_PARAMETERS)
    def test_enrich_ip_api_error_500(
        self,
        script_session: RRSSession,
        action_output: MockActionOutput,
        rrs: RansomwareResilience,
    ) -> None:
        """Test that Enrich IP handles a 500 server error gracefully."""
        rrs.enrich_ip_status_code = 500
        rrs.enrich_ip_response = {"error": "Internal Server Error"}

        enrich_ip_address.main()

        assert action_output.results.result_value is False
        assert action_output.results.execution_state.value == 2

    @set_metadata(integration_config_file_path=CONFIG_PATH, parameters=DEFAULT_PARAMETERS)
    def test_enrich_ip_api_error_401(
        self,
        script_session: RRSSession,
        action_output: MockActionOutput,
        rrs: RansomwareResilience,
    ) -> None:
        """Test that Enrich IP handles a 401 unauthorized error gracefully."""
        rrs.enrich_ip_status_code = 401
        rrs.enrich_ip_response = {"error": "Unauthorized"}

        enrich_ip_address.main()

        assert action_output.results.result_value is False
        assert action_output.results.execution_state.value == 2
