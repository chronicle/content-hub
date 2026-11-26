from __future__ import annotations

from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata

from rubrik_security_cloud.actions import get_ir_violation_details
from rubrik_security_cloud.tests.common import (
    CONFIG_PATH,
    IR_VIOLATION_ID,
    MOCK_IR_VIOLATION_DETAILS,
)
from rubrik_security_cloud.tests.core.product import RubrikSecurityCloud
from rubrik_security_cloud.tests.core.session import RubrikSession

DEFAULT_PARAMETERS = {"Violation ID": IR_VIOLATION_ID, "Policy Types": "Identity,IDP"}


class TestGetIRViolationDetails:
    @set_metadata(integration_config_file_path=CONFIG_PATH, parameters=DEFAULT_PARAMETERS)
    def test_get_ir_violation_details_success(
        self,
        script_session: RubrikSession,
        action_output: MockActionOutput,
        rubrik: RubrikSecurityCloud,
    ) -> None:
        rubrik.ir_violation_details_response = MOCK_IR_VIOLATION_DETAILS

        get_ir_violation_details.main()

        graphql_requests = [
            req for req in script_session.request_history if req.request.url.path.endswith("/api/graphql")
        ]
        assert len(graphql_requests) >= 1

        output_message = action_output.results.output_message
        assert f"Successfully retrieved IR violation details for ID: {IR_VIOLATION_ID}" in (output_message)
        assert "Test User" in output_message
        assert action_output.results.result_value is True
        assert action_output.results.execution_state.value == 0

    @set_metadata(integration_config_file_path=CONFIG_PATH, parameters=DEFAULT_PARAMETERS)
    def test_get_ir_violation_details_not_found(
        self,
        script_session: RubrikSession,
        action_output: MockActionOutput,
        rubrik: RubrikSecurityCloud,
    ) -> None:
        get_ir_violation_details.main()

        assert action_output.results.result_value is False
        assert action_output.results.execution_state.value == 2

    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        parameters={"Violation ID": "not-a-uuid", "Policy Types": "Identity,IDP"},
    )
    def test_get_ir_violation_details_invalid_id(
        self,
        script_session: RubrikSession,
        action_output: MockActionOutput,
        rubrik: RubrikSecurityCloud,
    ) -> None:
        get_ir_violation_details.main()

        assert action_output.results.result_value is False
        assert action_output.results.execution_state.value == 2
