from __future__ import annotations

from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata
from TIPCommon.base.action import ExecutionState

from ..common import CONFIG_PATH, load_action
from ..core.product import Infoblox
from ..core.session import InfobloxSession

InitiateIndicatorIntelLookupWithDossier = load_action("initiate_indicator_intel_lookup_with_dossier")


class TestInitiateIndicatorIntelLookupWithDossier:
    @set_metadata(
        parameters={"Indicator Type": "Host", "Indicator Value": "evil.example.com"},
        integration_config_file_path=CONFIG_PATH,
    )
    def test_success_without_wait_returns_job_id(
        self,
        script_session: InfobloxSession,
        action_output: MockActionOutput,
        infoblox: Infoblox,
    ) -> None:
        infoblox.set_dossier_initiate_response({"job_id": "job-1", "status": "PENDING"})

        InitiateIndicatorIntelLookupWithDossier.main()

        assert any(
            r.request.url.path.endswith("/tide/api/services/intel/lookup/indicator/host")
            for r in script_session.request_history
        )
        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert "Job ID and status returned" in action_output.results.output_message

    @set_metadata(
        parameters={
            "Indicator Type": "Host",
            "Indicator Value": "evil.example.com",
            "Wait for Results": "true",
        },
        integration_config_file_path=CONFIG_PATH,
    )
    def test_success_with_wait_returns_results(
        self,
        script_session: InfobloxSession,
        action_output: MockActionOutput,
        infoblox: Infoblox,
    ) -> None:
        infoblox.set_dossier_initiate_response({"results": [{"params": {"source": "whois"}, "status": "success"}]})

        InitiateIndicatorIntelLookupWithDossier.main()

        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert "Successfully retrieved 1 dossier results" in action_output.results.output_message

    @set_metadata(
        parameters={"Indicator Type": "Host", "Indicator Value": "evil.example.com"},
        integration_config_file_path=CONFIG_PATH,
    )
    def test_api_failure(
        self,
        script_session: InfobloxSession,
        action_output: MockActionOutput,
        infoblox: Infoblox,
    ) -> None:
        with infoblox.fail_requests(status_code=400, body={"error": "unsupported source"}):
            InitiateIndicatorIntelLookupWithDossier.main()

        assert action_output.results.execution_state == ExecutionState.FAILED
        assert "unsupported source" in action_output.results.output_message
