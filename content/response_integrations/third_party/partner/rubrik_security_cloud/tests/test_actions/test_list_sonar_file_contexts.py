from __future__ import annotations

from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata

from rubrik_security_cloud.actions import list_sonar_file_contexts
from rubrik_security_cloud.tests.common import CONFIG_PATH, MOCK_LIST_SONAR_FILE_CONTEXTS
from rubrik_security_cloud.tests.core.product import RubrikSecurityCloud
from rubrik_security_cloud.tests.core.session import RubrikSession

DEFAULT_PARAMETERS = {
    "Object ID": "obj-sonar-123",
    "Snapshot ID": "snapshot-sonar-456",
}


class TestListSonarFileContexts:
    @set_metadata(integration_config_file_path=CONFIG_PATH, parameters=DEFAULT_PARAMETERS)
    def test_list_sonar_file_contexts_success(
        self,
        script_session: RubrikSession,
        action_output: MockActionOutput,
        rubrik: RubrikSecurityCloud,
    ) -> None:
        rubrik.list_sonar_file_contexts_response = MOCK_LIST_SONAR_FILE_CONTEXTS
        success_output_msg_prefix = "Successfully retrieved"

        list_sonar_file_contexts.main()

        assert len(script_session.request_history) >= 1
        graphql_requests = [
            req
            for req in script_session.request_history
            if req.request.url.path.endswith("/api/graphql")
        ]
        assert len(graphql_requests) >= 1

        assert success_output_msg_prefix in action_output.results.output_message
        assert action_output.results.result_value is True
        assert action_output.results.execution_state.value == 0
