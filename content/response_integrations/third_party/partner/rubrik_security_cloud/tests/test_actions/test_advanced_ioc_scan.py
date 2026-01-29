from __future__ import annotations

from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata

from rubrik_security_cloud.actions import advanced_ioc_scan
from rubrik_security_cloud.tests.common import CONFIG_PATH, MOCK_ADVANCED_IOC_SCAN
from rubrik_security_cloud.tests.core.product import RubrikSecurityCloud
from rubrik_security_cloud.tests.core.session import RubrikSession

DEFAULT_PARAMETERS = {
    "Object ID": "obj-advanced-123,obj-advanced-456",
    "IOC Type": "HASH",
    "IOC Value": "abc123def456",
}


class TestAdvancedIOCScan:
    @set_metadata(integration_config_file_path=CONFIG_PATH, parameters=DEFAULT_PARAMETERS)
    def test_advanced_ioc_scan_success(
        self,
        script_session: RubrikSession,
        action_output: MockActionOutput,
        rubrik: RubrikSecurityCloud,
    ) -> None:
        rubrik.advanced_ioc_scan_response = MOCK_ADVANCED_IOC_SCAN
        success_output_msg_prefix = "Successfully started Advanced IOC Scan"

        advanced_ioc_scan.main()

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
