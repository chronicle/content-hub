from __future__ import annotations

from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata

from rubrik_security_cloud.actions import get_violation_file_list
from rubrik_security_cloud.tests.common import CONFIG_PATH, MOCK_VIOLATION_FILE_LIST
from rubrik_security_cloud.tests.core.product import RubrikSecurityCloud
from rubrik_security_cloud.tests.core.session import RubrikSession

DEFAULT_PARAMETERS = {
    "Object ID": "11111111-1111-1111-1111-111111111111",
    "Snapshot ID": "33333333-3333-3333-3333-333333333333",
    "Violation ID": "22222222-2222-2222-2222-222222222222",
    "Max Results": "25",
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
        success_output_msg_prefix = "Successfully retrieved 1 file(s)"

        get_violation_file_list.main()

        graphql_requests = [
            req
            for req in script_session.request_history
            if req.request.url.path.endswith("/api/graphql")
        ]
        assert len(graphql_requests) >= 1

        assert success_output_msg_prefix in action_output.results.output_message
        assert action_output.results.result_value is True
        assert action_output.results.execution_state.value == 0

    @set_metadata(integration_config_file_path=CONFIG_PATH, parameters=DEFAULT_PARAMETERS)
    def test_get_violation_file_list_no_results(
        self,
        script_session: RubrikSession,
        action_output: MockActionOutput,
        rubrik: RubrikSecurityCloud,
    ) -> None:
        rubrik.violation_file_list_response = {
            "data": {
                "policyObj": {
                    "fileResultConnection": {
                        "edges": [],
                        "pageInfo": {"hasNextPage": False, "endCursor": None},
                    }
                }
            }
        }

        get_violation_file_list.main()

        assert "No files found" in action_output.results.output_message
        assert action_output.results.result_value is True
        assert action_output.results.execution_state.value == 0
