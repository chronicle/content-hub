from __future__ import annotations

from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata

from rubrik_security_cloud.actions import search_dspm_violations
from rubrik_security_cloud.tests.common import CONFIG_PATH, MOCK_SEARCH_DSPM_VIOLATIONS
from rubrik_security_cloud.tests.core.product import RubrikSecurityCloud
from rubrik_security_cloud.tests.core.session import RubrikSession

DEFAULT_PARAMETERS = {}


class TestSearchDSPMViolations:
    @set_metadata(integration_config_file_path=CONFIG_PATH, parameters=DEFAULT_PARAMETERS)
    def test_search_dspm_violations_success(
        self,
        script_session: RubrikSession,
        action_output: MockActionOutput,
        rubrik: RubrikSecurityCloud,
    ) -> None:
        rubrik.search_dspm_violations_response = MOCK_SEARCH_DSPM_VIOLATIONS

        search_dspm_violations.main()

        graphql_requests = [
            req for req in script_session.request_history if req.request.url.path.endswith("/api/graphql")
        ]
        assert len(graphql_requests) >= 1

        assert "Successfully retrieved 1 DSPM violation(s)" in action_output.results.output_message
        assert action_output.results.result_value is True
        assert action_output.results.execution_state.value == 0

    @set_metadata(integration_config_file_path=CONFIG_PATH, parameters=DEFAULT_PARAMETERS)
    def test_search_dspm_violations_no_results(
        self,
        script_session: RubrikSession,
        action_output: MockActionOutput,
        rubrik: RubrikSecurityCloud,
    ) -> None:
        search_dspm_violations.main()

        assert "No DSPM violations found" in action_output.results.output_message
        assert action_output.results.result_value is True
        assert action_output.results.execution_state.value == 0

    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        parameters={"Max Results": "invalid"},
    )
    def test_search_dspm_violations_invalid_max_results(
        self,
        script_session: RubrikSession,
        action_output: MockActionOutput,
        rubrik: RubrikSecurityCloud,
    ) -> None:
        search_dspm_violations.main()

        assert action_output.results.result_value is False
        assert action_output.results.execution_state.value == 2

    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        parameters={
            "Detection Start Date": "2026-01-01T00:00:00Z",
            "Detection End Date": "2026-01-01T00:00:00Z",
        },
    )
    def test_search_dspm_violations_equal_dates(
        self,
        script_session: RubrikSession,
        action_output: MockActionOutput,
        rubrik: RubrikSecurityCloud,
    ) -> None:
        search_dspm_violations.main()

        assert "must be later than" in action_output.results.output_message
        assert action_output.results.result_value is False
        assert action_output.results.execution_state.value == 2
