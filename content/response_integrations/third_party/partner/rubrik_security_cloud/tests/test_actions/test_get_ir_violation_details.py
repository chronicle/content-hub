from __future__ import annotations

from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata

from rubrik_security_cloud.actions import get_ir_violation_details
from rubrik_security_cloud.tests.common import CONFIG_PATH, MOCK_IR_VIOLATION_DETAILS
from rubrik_security_cloud.tests.core.product import RubrikSecurityCloud
from rubrik_security_cloud.tests.core.session import RubrikSession

DEFAULT_PARAMETERS = {
    "Violation ID": "44444444-4444-4444-4444-444444444444",
    "Policy Types": "Identity,IDP",
}


class TestGetIRViolationDetails:
    @set_metadata(integration_config_file_path=CONFIG_PATH, parameters=DEFAULT_PARAMETERS)
    def test_get_ir_violation_details_success(
        self,
        script_session: RubrikSession,
        action_output: MockActionOutput,
        rubrik: RubrikSecurityCloud,
    ) -> None:
        rubrik.ir_violation_details_response = MOCK_IR_VIOLATION_DETAILS
        success_output_msg_prefix = "Successfully retrieved IR violation details"

        get_ir_violation_details.main()

        graphql_requests = [
            req
            for req in script_session.request_history
            if req.request.url.path.endswith("/api/graphql")
        ]
        assert len(graphql_requests) >= 1

        assert success_output_msg_prefix in action_output.results.output_message
        assert action_output.results.result_value is True
        assert action_output.results.execution_state.value == 0

    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        parameters={
            "Violation ID": "bad-uuid",
            "Policy Types": "Identity,IDP",
        },
    )
    def test_get_ir_violation_details_invalid_uuid(
        self,
        script_session: RubrikSession,
        action_output: MockActionOutput,
        rubrik: RubrikSecurityCloud,
    ) -> None:
        get_ir_violation_details.main()

        assert action_output.results.result_value is False
        assert action_output.results.execution_state.value == 2
