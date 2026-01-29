from __future__ import annotations

from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata

from rubrik_security_cloud.actions import get_sonar_sensitive_hits
from rubrik_security_cloud.tests.common import (
    CONFIG_PATH,
    MOCK_SONAR_OBJECT_DETAIL,
    MOCK_SONAR_POLICY_OBJECTS_LIST,
)
from rubrik_security_cloud.tests.core.product import RubrikSecurityCloud
from rubrik_security_cloud.tests.core.session import RubrikSession

DEFAULT_PARAMETERS = {
    "Object Name": "test-object",
    "Lookback Days": "7",
}


class TestGetSonarSensitiveHits:
    @set_metadata(integration_config_file_path=CONFIG_PATH, parameters=DEFAULT_PARAMETERS)
    def test_get_sonar_sensitive_hits_success(
        self,
        script_session: RubrikSession,
        action_output: MockActionOutput,
        rubrik: RubrikSecurityCloud,
    ) -> None:
        rubrik.sonar_policy_objects_list_response = MOCK_SONAR_POLICY_OBJECTS_LIST
        rubrik.sonar_object_detail_response = MOCK_SONAR_OBJECT_DETAIL
        success_output_msg_prefix = (
            "Successfully retrieved Sonar Sensitive Hits for Object: test-object"
        )

        get_sonar_sensitive_hits.main()

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
