from __future__ import annotations

from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata

from rubrik_security_cloud.actions import get_cdm_cluster_location
from rubrik_security_cloud.tests.common import CONFIG_PATH, MOCK_CDM_CLUSTER_LOCATION
from rubrik_security_cloud.tests.core.product import RubrikSecurityCloud
from rubrik_security_cloud.tests.core.session import RubrikSession

DEFAULT_PARAMETERS = {
    "Cluster ID": "test-cluster-123",
}


class TestGetCDMClusterLocation:
    @set_metadata(integration_config_file_path=CONFIG_PATH, parameters=DEFAULT_PARAMETERS)
    def test_get_cdm_cluster_location_success(
        self,
        script_session: RubrikSession,
        action_output: MockActionOutput,
        rubrik: RubrikSecurityCloud,
    ) -> None:
        rubrik.cdm_cluster_location_response = MOCK_CDM_CLUSTER_LOCATION
        success_output_msg = (
            "Successfully retrieved CDM Cluster Location for Cluster ID: test-cluster-123"
        )

        get_cdm_cluster_location.main()

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
