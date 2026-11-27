"""
Action script for DomainTools - Get Domain Profile.

Builds a comprehensive dossier for each in-scope domain using DomainTools Iris Investigate.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyUtils import output_handler
from TIPCommon.extraction import extract_configuration_param
from TIPCommon.transformation import construct_csv

from ..core.constants import GET_DOMAIN_PROFILE_SCRIPT_NAME, INTEGRATION_NAME
from ..core.DomainToolsManager import DomainToolsManager
from ..core.UtilsManager import classify_domain_risk, extract_domain_from_string, parse_domain_age_days

if TYPE_CHECKING:
    from soar_sdk.SiemplifyDataModel import DomainEntityInfo
    from TIPCommon.types import SingleJson

    from ..core.datamodels import IrisInvestigateModel

SUPPORTED_ENTITY_TYPES: list[str] = [EntityTypes.URL, EntityTypes.HOSTNAME, EntityTypes.DOMAIN]


@dataclass(slots=True)
class _ProfileOutcome:
    json_results: list[SingleJson] = field(default_factory=list)
    csv_rows: list[SingleJson] = field(default_factory=list)
    success_entities: list[DomainEntityInfo] = field(default_factory=list)
    failed_entities: list[DomainEntityInfo] = field(default_factory=list)
    missing_domains: list[str] = field(default_factory=list)


def _extract_params(siemplify: SiemplifyAction) -> tuple[str, str, str]:
    username: str = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Username",
        is_mandatory=True,
        print_value=True,
    )
    api_key: str = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="ApiToken",
        is_mandatory=True,
        print_value=True,
    )
    verify_ssl: str = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        is_mandatory=True,
    )
    return username, api_key, verify_ssl


def _build_domain_profile(
    iris_model: IrisInvestigateModel,
    domain_age_days: int | None,
    risk_category: str,
) -> SingleJson:
    return {
        "risk": {
            "overall_risk_score": iris_model.analytics.overall_risk_score,
            "proximity_risk_score": iris_model.analytics.proximity_risk_score,
            "threat_profile_risk_score": iris_model.analytics.threat_profile_risk_score.risk_score,
            "malware_risk_score": iris_model.analytics.malware_risk_score,
            "phishing_risk_score": iris_model.analytics.phishing_risk_score,
            "spam_risk_score": iris_model.analytics.spam_risk_score,
            "threats": iris_model.analytics.threat_profile_risk_score.threats,
            "evidence": iris_model.analytics.threat_profile_risk_score.evidence,
        },
        "identity": {
            "registrant_name": iris_model.identity.registrant_name,
            "registrant_org": iris_model.identity.registrant_org,
            "registrar": iris_model.identity.registrar,
            "soa_email": iris_model.identity.soa_email,
            "email_domains": iris_model.identity.email_domains,
        },
        "registration": {
            "create_date": iris_model.registration.create_date,
            "expiration_date": iris_model.registration.expiration_date,
            "domain_status": iris_model.registration.domain_status,
            "registrar_status": iris_model.registration.registrar_status,
        },
        "hosting": {
            "ip_addresses": iris_model.hosting.ip_addresses,
            "ip_country_code": iris_model.hosting.ip_country_code,
            "name_servers": iris_model.hosting.name_servers,
            "mx_servers": iris_model.hosting.mx_servers,
            "ssl_certificates": iris_model.hosting.ssl_certificates,
        },
        "metadata": {
            "last_enriched": datetime.now().strftime("%Y-%m-%d"),
            "domain_age_days": domain_age_days,
            "risk_category": risk_category,
        },
    }


def _write_results(siemplify: SiemplifyAction, outcome: _ProfileOutcome) -> None:
    siemplify.update_entities(outcome.success_entities)
    if outcome.missing_domains:
        outcome.json_results.append(
            {"Entity": "MissingDomains", "EntityResult": {"missing_domains": outcome.missing_domains}}
        )
    siemplify.result.add_result_json(outcome.json_results)
    if outcome.csv_rows:
        siemplify.result.add_data_table("Domain Profile", construct_csv(outcome.csv_rows))


def _build_summary_message(outcome: _ProfileOutcome) -> str:
    total = len(outcome.success_entities) + len(outcome.failed_entities) + len(outcome.missing_domains)
    msg = f"Successfully built profiles for {len(outcome.success_entities)} of {total} domain(s)."
    if outcome.failed_entities:
        msg += f"\nFailed to profile: {', '.join(str(e.identifier) for e in outcome.failed_entities)}"
    if outcome.missing_domains:
        msg += f"\nNot returned by API: {', '.join(outcome.missing_domains)}"
    return msg


@output_handler
def main() -> None:
    siemplify = SiemplifyAction()
    siemplify.script_name = GET_DOMAIN_PROFILE_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Get Domain Profile Started -----------------")

    username, api_key, verify_ssl = _extract_params(siemplify)

    status: int = EXECUTION_STATE_COMPLETED
    output_message: str = ""
    result_value: bool = True

    domain_entity_map: dict[str, list[DomainEntityInfo]] = {}
    for entity in siemplify.target_entities:
        if entity.entity_type not in SUPPORTED_ENTITY_TYPES:
            continue
        if domain := extract_domain_from_string(entity.identifier):
            domain_entity_map.setdefault(domain, []).append(entity)

    if not domain_entity_map:
        output_message = "No domain profiles could be built."
        result_value = False
        siemplify.end(output_message, result_value, status)
        return

    outcome = _ProfileOutcome()

    try:
        dt_manager = DomainToolsManager(
            username=username,
            api_key=api_key,
            verify_ssl=verify_ssl,
            siemplify_logger=siemplify.LOGGER,
        )

        try:
            iris_models = dt_manager.investigate_domains(domains=list(domain_entity_map.keys()))
        except Exception as api_err:
            siemplify.LOGGER.error(f"Failed to retrieve domain profiles: {api_err}")
            output_message = "No domain profiles could be built."
            result_value = False
            siemplify.end(output_message, result_value, status)
            return

        iris_model_map = {m.domain: m for m in iris_models}
        outcome.missing_domains = [d for d in domain_entity_map if d not in iris_model_map]

        for domain, entities in domain_entity_map.items():
            iris_model = iris_model_map.get(domain)
            if not iris_model:
                continue
            siemplify.LOGGER.info(f"Building profile for: {domain}")
            try:
                domain_age_days = parse_domain_age_days(iris_model.registration.create_date)
                risk_category = classify_domain_risk(iris_model.analytics.overall_risk_score, domain_age_days)
                profile = _build_domain_profile(iris_model, domain_age_days, risk_category)
                outcome.csv_rows.append(iris_model.to_table_data())
                for entity in entities:
                    outcome.json_results.append({"Entity": entity.identifier, "EntityResult": profile})
                    entity.is_enriched = True
                    outcome.success_entities.append(entity)
            except Exception as e:
                outcome.failed_entities.extend(entities)
                siemplify.LOGGER.error(f"Failed to build profile for {domain}. Reason: {str(e)}")
                siemplify.LOGGER.exception(e)

        if outcome.success_entities:
            _write_results(siemplify, outcome)
            output_message = _build_summary_message(outcome)
        else:
            output_message = "No domain profiles could be built."
            result_value = False

    except Exception as err:
        output_message = f"Error running action: {str(err)}"
        status = EXECUTION_STATE_FAILED
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(err)
        result_value = False

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}, Result: {result_value}, Output: {output_message}")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
