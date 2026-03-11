from __future__ import annotations

from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata

from netappransomwareresilience.actions import enrich_storage
from netappransomwareresilience.tests.common import CONFIG_PATH, MOCK_ENRICH_STORAGE_RESPONSE
from netappransomwareresilience.tests.core.product import RansomwareResilience
from netappransomwareresilience.tests.core.session import RRSSession

DEFAULT_PARAMETERS = {
    "Agent ID": "EAvI3XQqTeYvuiKeIlpBNPPl6n1ZxnAAclients",
    "System ID": "VsaWorkingEnvironment-A2hoS8xl",
}


class TestEnrichStorage:
    @set_metadata(integration_config_file_path=CONFIG_PATH, parameters=DEFAULT_PARAMETERS)
    def test_enrich_storage_success(
        self,
        script_session: RRSSession,
        action_output: MockActionOutput,
        rrs: RansomwareResilience,
    ) -> None:
        """Test that Enrich Storage action succeeds."""
        rrs.enrich_storage_response = MOCK_ENRICH_STORAGE_RESPONSE
        success_output_msg = "Successfully enriched storage information"

        enrich_storage.main()

        assert len(script_session.request_history) >= 1
        storage_requests = [
            req
            for req in script_session.request_history
            if "enrich/storage" in req.request.url.path
        ]
        assert len(storage_requests) >= 1

        assert action_output.results.output_message == success_output_msg
        assert action_output.results.result_value is True
        assert action_output.results.execution_state.value == 0

    @set_metadata(integration_config_file_path=CONFIG_PATH, parameters=DEFAULT_PARAMETERS)
    def test_enrich_storage_api_error_500(
        self,
        script_session: RRSSession,
        action_output: MockActionOutput,
        rrs: RansomwareResilience,
    ) -> None:
        """Test that Enrich Storage handles a 500 server error gracefully."""
        rrs.enrich_storage_status_code = 500
        rrs.enrich_storage_response = {"error": "Internal Server Error"}

        enrich_storage.main()

        assert action_output.results.result_value is False
        assert action_output.results.execution_state.value == 2

    @set_metadata(integration_config_file_path=CONFIG_PATH, parameters=DEFAULT_PARAMETERS)
    def test_enrich_storage_api_error_401(
        self,
        script_session: RRSSession,
        action_output: MockActionOutput,
        rrs: RansomwareResilience,
    ) -> None:
        """Test that Enrich Storage handles a 401 unauthorized error gracefully."""
        rrs.enrich_storage_status_code = 401
        rrs.enrich_storage_response = {"error": "Unauthorized"}

        enrich_storage.main()

        assert action_output.results.result_value is False
        assert action_output.results.execution_state.value == 2
