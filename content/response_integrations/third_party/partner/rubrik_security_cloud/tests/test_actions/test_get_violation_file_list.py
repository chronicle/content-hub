from __future__ import annotations

from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata

from rubrik_security_cloud.actions import get_violation_file_list
from rubrik_security_cloud.tests.common import (
    CONFIG_PATH,
    DSPM_VIOLATION_ID,
    MOCK_VIOLATION_FILE_LIST,
    OBJECT_ID,
    SNAPSHOT_ID,
)
from rubrik_security_cloud.tests.core.product import RubrikSecurityCloud
from rubrik_security_cloud.tests.core.session import RubrikSession

DEFAULT_PARAMETERS = {
    "Object ID": OBJECT_ID,
    "Snapshot ID": SNAPSHOT_ID,
    "Violation ID": DSPM_VIOLATION_ID,
}


class TestGetViolationFileList:
    @set_metadata(integration_config_file_path=CONFIG_PATH, parameters=DEFAULT_PARAMETERS)
    def test_get_violation_file_list_success(
        self,
        script_session: RubrikSession,
        action_output: MockActionOutput,
        rubrik: RubrikSecurityCloud,
    ) -> None:
        rubrik.violation_file_list_response = MOCK_VIOLATION_FILE_LIST

        get_violation_file_list.main()

        graphql_requests = [
            req for req in script_session.request_history if req.request.url.path.endswith("/api/graphql")
        ]
        assert len(graphql_requests) >= 1

        assert (
            f"Successfully retrieved 1 file(s) for violation ID: {DSPM_VIOLATION_ID}"
            in action_output.results.output_message
        )
        assert action_output.results.result_value is True
        assert action_output.results.execution_state.value == 0

    @set_metadata(integration_config_file_path=CONFIG_PATH, parameters=DEFAULT_PARAMETERS)
    def test_get_violation_file_list_no_results(
        self,
        script_session: RubrikSession,
        action_output: MockActionOutput,
        rubrik: RubrikSecurityCloud,
    ) -> None:
        get_violation_file_list.main()

        assert "No files found" in action_output.results.output_message
        assert action_output.results.result_value is True
        assert action_output.results.execution_state.value == 0

    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        parameters={**DEFAULT_PARAMETERS, "Object ID": "not-a-uuid"},
    )
    def test_get_violation_file_list_invalid_object_id(
        self,
        script_session: RubrikSession,
        action_output: MockActionOutput,
        rubrik: RubrikSecurityCloud,
    ) -> None:
        get_violation_file_list.main()

        assert action_output.results.result_value is False
        assert action_output.results.execution_state.value == 2
