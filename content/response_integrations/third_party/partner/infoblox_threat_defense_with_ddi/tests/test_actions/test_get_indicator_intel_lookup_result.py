from __future__ import annotations

from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata
from TIPCommon.base.action import ExecutionState

from ..common import CONFIG_PATH, load_action
from ..core.product import Infoblox
from ..core.session import InfobloxSession

GetIndicatorIntelLookupResult = load_action("get_indicator_intel_lookup_result")


class TestGetIndicatorIntelLookupResult:
    @set_metadata(parameters={"Job ID": "job-1"}, integration_config_file_path=CONFIG_PATH)
    def test_success(
        self,
        script_session: InfobloxSession,
        action_output: MockActionOutput,
        infoblox: Infoblox,
    ) -> None:
        infoblox.set_dossier_result_response({"results": [{"params": {"source": "whois"}, "status": "success"}]})

        GetIndicatorIntelLookupResult.main()

        assert any(
            r.request.url.path.endswith("/tide/api/services/intel/lookup/jobs/job-1/results")
            for r in script_session.request_history
        )
        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert "Successfully retrieved 1 dossier results" in action_output.results.output_message

    @set_metadata(parameters={"Job ID": "job-1"}, integration_config_file_path=CONFIG_PATH)
    def test_no_results_found(
        self,
        script_session: InfobloxSession,
        action_output: MockActionOutput,
        infoblox: Infoblox,
    ) -> None:
        infoblox.set_dossier_result_response({"results": []})

        GetIndicatorIntelLookupResult.main()

        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert "No dossier results found" in action_output.results.output_message

    @set_metadata(parameters={"Job ID": "missing-job"}, integration_config_file_path=CONFIG_PATH)
    def test_job_not_found_fails(
        self,
        script_session: InfobloxSession,
        action_output: MockActionOutput,
        infoblox: Infoblox,
    ) -> None:
        with infoblox.fail_requests(status_code=404, body={"error": "no such job"}):
            GetIndicatorIntelLookupResult.main()

        assert action_output.results.execution_state == ExecutionState.FAILED
        assert "Job ID does not exist" in action_output.results.output_message
