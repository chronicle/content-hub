from __future__ import annotations

from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata
from TIPCommon.base.action import ExecutionState

from domain_tools.actions import GetDomainProfile
from domain_tools.core.datamodels import (
    Analytics,
    Hosting,
    Identity,
    IrisInvestigateModel,
    ParsedDomainRDAPModel,
    Registration,
    RiskProfile,
    WhoisHistoryModel,
)
from domain_tools.tests.common import CONFIG_PATH
from domain_tools.tests.conftest import MockDomainToolsManager

DOMAIN_ENTITY = {"identifier": "example.com", "entity_type": "DOMAIN", "additional_properties": {}}


def _make_iris_model(domain: str = "example.com") -> IrisInvestigateModel:
    return IrisInvestigateModel(
        name=domain,
        last_enriched="2026-07-18",
        analytics=Analytics(
            overall_risk_score=23,
            proximity_risk_score=10,
            threat_profile_risk_score=RiskProfile(risk_score=5, threats=[], evidence=[]),
        ),
        identity=Identity(
            registrant_name="Example Registrant",
            registrant_org="Example Corp",
            registrar="Example Registrar Inc.",
        ),
        registration=Registration(
            create_date="2013-12-06",
            expiration_date="2026-12-06",
            domain_status=True,
        ),
        hosting=Hosting(ip_country_code="us"),
    )


def _make_rdap_model() -> ParsedDomainRDAPModel:
    return ParsedDomainRDAPModel(domain="example.com", has_found=True)


def _make_whois_model() -> WhoisHistoryModel:
    return WhoisHistoryModel(record_count=2)


class TestGetDomainProfile:

    @set_metadata(integration_config_file_path=CONFIG_PATH, entities=[DOMAIN_ENTITY])
    def test_profile_success(
        self, action_output: MockActionOutput, dt_manager: MockDomainToolsManager
    ):
        dt_manager.set_investigate_domains_response([_make_iris_model()])
        dt_manager.set_parsed_domain_rdap_response(_make_rdap_model())
        dt_manager.set_whois_history_response(_make_whois_model())

        GetDomainProfile.main()

        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert action_output.results.result_value is True
        assert "Successfully built profiles for 1 domain(s)" in action_output.results.output_message

    @set_metadata(integration_config_file_path=CONFIG_PATH, entities=[])
    def test_no_entities(
        self, action_output: MockActionOutput, dt_manager: MockDomainToolsManager
    ):
        GetDomainProfile.main()

        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert action_output.results.result_value is False
        assert "No domain profiles could be built" in action_output.results.output_message

    @set_metadata(integration_config_file_path=CONFIG_PATH, entities=[DOMAIN_ENTITY])
    def test_investigate_failure(
        self, action_output: MockActionOutput, dt_manager: MockDomainToolsManager
    ):
        dt_manager.simulate_investigate_failure()

        GetDomainProfile.main()

        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert action_output.results.result_value is False
        assert "No domain profiles could be built" in action_output.results.output_message

    @set_metadata(integration_config_file_path=CONFIG_PATH, entities=[DOMAIN_ENTITY])
    def test_rdap_not_found_still_succeeds(
        self, action_output: MockActionOutput, dt_manager: MockDomainToolsManager
    ):
        dt_manager.set_investigate_domains_response([_make_iris_model()])
        dt_manager.set_parsed_domain_rdap_response(
            ParsedDomainRDAPModel(domain="example.com", has_found=False)
        )
        dt_manager.set_whois_history_response(_make_whois_model())

        GetDomainProfile.main()

        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert action_output.results.result_value is True

    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        entities=[
            DOMAIN_ENTITY,
            {"identifier": "evil.com", "entity_type": "DOMAIN", "additional_properties": {}},
        ],
    )
    def test_multiple_entities(
        self, action_output: MockActionOutput, dt_manager: MockDomainToolsManager
    ):
        dt_manager.set_investigate_domains_response([_make_iris_model()])
        dt_manager.set_parsed_domain_rdap_response(_make_rdap_model())
        dt_manager.set_whois_history_response(_make_whois_model())

        GetDomainProfile.main()

        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert "2 domain(s)" in action_output.results.output_message
