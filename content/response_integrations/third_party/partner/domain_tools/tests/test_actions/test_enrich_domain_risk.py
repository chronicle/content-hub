from __future__ import annotations

from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata
from TIPCommon.base.action import ExecutionState

from domain_tools.actions import EnrichDomainRisk
from domain_tools.core.datamodels import EnrichedDomainSummary
from domain_tools.tests.common import CONFIG_PATH
from domain_tools.tests.conftest import MockDomainToolsManager

DOMAIN_ENTITY = {"identifier": "evil.com", "entity_type": "DOMAIN", "additional_properties": {}}

HIGH_RISK_RESULT = EnrichedDomainSummary(
    domain="evil.com",
    risk_category="high_risk",
    overall_risk_score=87,
    proximity_risk_score=45,
    threat_profile_risk_score=87,
    malware_risk_score=72,
    phishing_risk_score=55,
    spam_risk_score=30,
    threat_profile_threats=["malware", "phishing"],
    threat_profile_evidence=["blacklisted"],
    create_date="2024-01-15",
    domain_age_days=550,
    is_young_domain=False,
    registrant_org="Unknown LLC",
    ip_country_code="ru",
    iris_investigate_link='https://iris.domaintools.com/investigate/search/?q=domain:"evil.com"',
)

YOUNG_DOMAIN_RESULT = EnrichedDomainSummary(
    domain="newdomain.com",
    risk_category="young_domain",
    overall_risk_score=10,
    domain_age_days=5,
    is_young_domain=True,
    iris_investigate_link='https://iris.domaintools.com/investigate/search/?q=domain:"newdomain.com"',
)


class TestEnrichDomainRisk:

    @set_metadata(integration_config_file_path=CONFIG_PATH, entities=[DOMAIN_ENTITY])
    def test_enrich_success(
        self, action_output: MockActionOutput, dt_manager: MockDomainToolsManager
    ):
        dt_manager.set_enrich_domains_response([HIGH_RISK_RESULT])

        EnrichDomainRisk.main()

        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert action_output.results.result_value is True
        assert "Successfully enriched 1 domain(s)" in action_output.results.output_message
        assert "1 marked as suspicious" in action_output.results.output_message

    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        entities=[{"identifier": "newdomain.com", "entity_type": "DOMAIN", "additional_properties": {}}],
    )
    def test_young_domain_not_suspicious_below_threshold(
        self, action_output: MockActionOutput, dt_manager: MockDomainToolsManager
    ):
        # score 10 is below default threshold (70) — young domain age alone does not flag suspicious
        dt_manager.set_enrich_domains_response([YOUNG_DOMAIN_RESULT])

        EnrichDomainRisk.main()

        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert "0 marked as suspicious" in action_output.results.output_message

    @set_metadata(integration_config_file_path=CONFIG_PATH, entities=[])
    def test_no_entities(
        self, action_output: MockActionOutput, dt_manager: MockDomainToolsManager
    ):
        EnrichDomainRisk.main()

        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert action_output.results.result_value is False
        assert "No domain entities found" in action_output.results.output_message

    @set_metadata(integration_config_file_path=CONFIG_PATH, entities=[DOMAIN_ENTITY])
    def test_api_failure(
        self, action_output: MockActionOutput, dt_manager: MockDomainToolsManager
    ):
        dt_manager.simulate_enrich_failure()

        EnrichDomainRisk.main()

        assert action_output.results.execution_state == ExecutionState.FAILED
        assert action_output.results.result_value is False
        assert "Error running action" in action_output.results.output_message

    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        parameters={"Risk Threshold": "50"},
        entities=[DOMAIN_ENTITY],
    )
    def test_custom_threshold(
        self, action_output: MockActionOutput, dt_manager: MockDomainToolsManager
    ):
        low_score = EnrichedDomainSummary(
            domain="evil.com",
            risk_category="medium_risk",
            overall_risk_score=55,
            domain_age_days=200,
            is_young_domain=False,
            iris_investigate_link="",
        )
        dt_manager.set_enrich_domains_response([low_score])

        EnrichDomainRisk.main()

        assert action_output.results.execution_state == ExecutionState.COMPLETED
        # score 55 >= threshold 50 → marked suspicious
        assert "1 marked as suspicious" in action_output.results.output_message
