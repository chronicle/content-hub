from __future__ import annotations

from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata
from TIPCommon.base.action import ExecutionState

from domain_tools.actions import BulkEnrichDomains
from domain_tools.core.datamodels import EnrichedDomainSummary
from domain_tools.tests.common import CONFIG_PATH
from domain_tools.tests.conftest import MockDomainToolsManager

DOMAIN_ENTITY = {"identifier": "evil.com", "entity_type": "DOMAIN", "additional_properties": {}}

BULK_RESULTS = [
    EnrichedDomainSummary(
        domain="evil.com",
        risk_category="high_risk",
        overall_risk_score=87,
        domain_age_days=550,
        is_young_domain=False,
        iris_investigate_link="",
    ),
    EnrichedDomainSummary(
        domain="google.com",
        risk_category="low_risk",
        overall_risk_score=5,
        domain_age_days=10000,
        is_young_domain=False,
        iris_investigate_link="",
    ),
]


class TestBulkEnrichDomains:

    @set_metadata(integration_config_file_path=CONFIG_PATH, entities=[DOMAIN_ENTITY])
    def test_bulk_enrich_from_entities(
        self, action_output: MockActionOutput, dt_manager: MockDomainToolsManager
    ):
        dt_manager.set_enrich_domains_response(BULK_RESULTS)

        BulkEnrichDomains.main()

        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert action_output.results.result_value is True
        assert "1 high risk" in action_output.results.output_message
        assert "1 low risk" in action_output.results.output_message

    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        parameters={"Domains": "evil.com, google.com"},
        entities=[],
    )
    def test_bulk_enrich_from_param(
        self, action_output: MockActionOutput, dt_manager: MockDomainToolsManager
    ):
        dt_manager.set_enrich_domains_response(BULK_RESULTS)

        BulkEnrichDomains.main()

        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert "Enriched 2 domain(s)" in action_output.results.output_message

    @set_metadata(integration_config_file_path=CONFIG_PATH, entities=[])
    def test_no_domains(
        self, action_output: MockActionOutput, dt_manager: MockDomainToolsManager
    ):
        BulkEnrichDomains.main()

        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert action_output.results.result_value is False
        assert "No domains provided" in action_output.results.output_message

    @set_metadata(integration_config_file_path=CONFIG_PATH, entities=[DOMAIN_ENTITY])
    def test_api_failure(
        self, action_output: MockActionOutput, dt_manager: MockDomainToolsManager
    ):
        dt_manager.simulate_enrich_failure()

        BulkEnrichDomains.main()

        assert action_output.results.execution_state == ExecutionState.FAILED
        assert "Error running action" in action_output.results.output_message

    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        parameters={"Include Young Domains": "false"},
        entities=[DOMAIN_ENTITY],
    )
    def test_exclude_young_domains(
        self, action_output: MockActionOutput, dt_manager: MockDomainToolsManager
    ):
        young_result = EnrichedDomainSummary(
            domain="evil.com",
            risk_category="young_domain",
            overall_risk_score=10,
            domain_age_days=5,
            is_young_domain=True,
            iris_investigate_link="",
        )
        dt_manager.set_enrich_domains_response([young_result])

        BulkEnrichDomains.main()

        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert "1 young domains" in action_output.results.output_message
