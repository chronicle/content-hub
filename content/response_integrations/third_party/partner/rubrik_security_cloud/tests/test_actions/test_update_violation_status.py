from __future__ import annotations

from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata

from rubrik_security_cloud.actions import update_violation_status
from rubrik_security_cloud.tests.common import CONFIG_PATH, MOCK_UPDATE_VIOLATION_STATUS
from rubrik_security_cloud.tests.core.product import RubrikSecurityCloud
from rubrik_security_cloud.tests.core.session import RubrikSession

DEFAULT_PARAMETERS = {
    "Violation ID": "22222222-2222-2222-2222-222222222222",
    "New Status": "Remediated",
}


class TestUpdateViolationStatus:
    @set_metadata(integration_config_file_path=CONFIG_PATH, parameters=DEFAULT_PARAMETERS)
    def test_update_violation_status_success(
        self,
        script_session: RubrikSession,
        action_output: MockActionOutput,
        rubrik: RubrikSecurityCloud,
    ) -> None:
        rubrik.update_violation_status_response = MOCK_UPDATE_VIOLATION_STATUS
        success_output_msg_prefix = "Violation status updated to 'Remediated'"

        update_violation_status.main()

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
            "Violation ID": "22222222-2222-2222-2222-222222222222",
            "New Status": "NotARealStatus",
        },
    )
    def test_update_violation_status_invalid_status(
        self,
        script_session: RubrikSession,
        action_output: MockActionOutput,
        rubrik: RubrikSecurityCloud,
    ) -> None:
        update_violation_status.main()

        assert "Invalid value" in action_output.results.output_message
        assert action_output.results.result_value is False
        assert action_output.results.execution_state.value == 2
