from __future__ import annotations

import json

from integration_testing.common import get_request_payload
from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata

from rubrik_security_cloud.actions import update_violation_status
from rubrik_security_cloud.tests.common import (
    CONFIG_PATH,
    DSPM_VIOLATION_ID,
    MOCK_UPDATE_VIOLATION_STATUS,
)
from rubrik_security_cloud.tests.core.product import RubrikSecurityCloud
from rubrik_security_cloud.tests.core.session import RubrikSession

DEFAULT_PARAMETERS = {"Violation ID": DSPM_VIOLATION_ID, "New Status": "In Progress"}


def _graphql_payload(request) -> dict:
    """GraphQL body of a recorded request; APIManager sends it as a JSON string in `data`."""
    payload = get_request_payload(request)
    if payload:
        return payload
    data = (getattr(request, "kwargs", None) or {}).get("data")
    return json.loads(data) if isinstance(data, str) else data or {}


class TestUpdateViolationStatus:
    @set_metadata(integration_config_file_path=CONFIG_PATH, parameters=DEFAULT_PARAMETERS)
    def test_update_violation_status_success(
        self,
        script_session: RubrikSession,
        action_output: MockActionOutput,
        rubrik: RubrikSecurityCloud,
    ) -> None:
        rubrik.update_violation_status_response = MOCK_UPDATE_VIOLATION_STATUS

        update_violation_status.main()

        mutation_payloads = [
            _graphql_payload(req.request)
            for req in script_session.request_history
            if req.request.url.path.endswith("/api/graphql")
        ]
        mutation_payloads = [
            payload for payload in mutation_payloads if "bulkUpdatePolicyViolations" in payload.get("query", "")
        ]
        assert len(mutation_payloads) == 1
        mutation_input = mutation_payloads[0]["variables"]["input"]
        assert mutation_input["policyViolationIds"] == [DSPM_VIOLATION_ID]
        assert mutation_input["newPolicyViolationStatus"] == "POLICY_VIOLATION_STATUS_IN_PROGRESS"

        assert (
            f"Violation status updated to 'In Progress' for violation ID: {DSPM_VIOLATION_ID}"
            in action_output.results.output_message
        )
        assert action_output.results.result_value is True
        assert action_output.results.execution_state.value == 0

    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        parameters={"Violation ID": DSPM_VIOLATION_ID, "New Status": "Unknown"},
    )
    def test_update_violation_status_invalid_status(
        self,
        script_session: RubrikSession,
        action_output: MockActionOutput,
        rubrik: RubrikSecurityCloud,
    ) -> None:
        update_violation_status.main()

        assert action_output.results.result_value is False
        assert action_output.results.execution_state.value == 2

    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        parameters={"Violation ID": "not-a-uuid", "New Status": "In Progress"},
    )
    def test_update_violation_status_invalid_id(
        self,
        script_session: RubrikSession,
        action_output: MockActionOutput,
        rubrik: RubrikSecurityCloud,
    ) -> None:
        update_violation_status.main()

        assert action_output.results.result_value is False
        assert action_output.results.execution_state.value == 2
