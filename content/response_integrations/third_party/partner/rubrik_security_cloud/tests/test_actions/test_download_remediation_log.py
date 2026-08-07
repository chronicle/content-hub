from __future__ import annotations

from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata

from rubrik_security_cloud.actions import download_remediation_log
from rubrik_security_cloud.tests.common import (
    CONFIG_PATH,
    MOCK_ALL_USER_FILES,
    MOCK_DSPM_VIOLATION_DETAILS,
)
from rubrik_security_cloud.tests.core.product import RubrikSecurityCloud
from rubrik_security_cloud.tests.core.session import RubrikSession

DEFAULT_PARAMETERS = {
    "Object ID": "11111111-1111-1111-1111-111111111111",
    "Violation ID": "22222222-2222-2222-2222-222222222222",
    "Object Name": "TestObject",
}


class TestDownloadRemediationLog:
    @set_metadata(integration_config_file_path=CONFIG_PATH, parameters=DEFAULT_PARAMETERS)
    def test_first_run_triggers_and_locates_file(
        self,
        script_session: RubrikSession,
        action_output: MockActionOutput,
        rubrik: RubrikSecurityCloud,
    ) -> None:
        # Validate inputs -> create remediation log -> locate the pending file,
        # ending IN_PROGRESS.
        rubrik.dspm_violation_details_response = MOCK_DSPM_VIOLATION_DETAILS
        rubrik.all_user_files_response = MOCK_ALL_USER_FILES

        download_remediation_log.main(True)

        graphql_requests = [
            req
            for req in script_session.request_history
            if req.request.url.path.endswith("/api/graphql")
        ]
        assert len(graphql_requests) >= 1

        assert "Waiting for remediation log" in action_output.results.output_message
        # IN_PROGRESS keeps the action polling on the next run.
        assert action_output.results.execution_state.value == 1

    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        parameters={
            "Object ID": "88888888-8888-8888-8888-888888888888",
            "Violation ID": "22222222-2222-2222-2222-222222222222",
            "Object Name": "TestObject",
        },
    )
    def test_first_run_object_id_mismatch_fails(
        self,
        script_session: RubrikSession,
        action_output: MockActionOutput,
        rubrik: RubrikSecurityCloud,
    ) -> None:
        rubrik.dspm_violation_details_response = MOCK_DSPM_VIOLATION_DETAILS

        download_remediation_log.main(True)

        assert action_output.results.result_value is False
        assert action_output.results.execution_state.value == 2
