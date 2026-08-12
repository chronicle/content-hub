"""
Action script for DomainTools - Get Domain Profile.

Builds a comprehensive dossier for each in-scope domain by combining
Iris Investigate, RDAP, and WHOIS history data.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyUtils import output_handler
from TIPCommon.extraction import extract_configuration_param
from TIPCommon.transformation import construct_csv

from ..core.constants import GET_DOMAIN_PROFILE_SCRIPT_NAME, INTEGRATION_NAME
from ..core.DomainToolsManager import DomainToolsManager
from ..core.UtilsManager import classify_domain_risk, extract_domain_from_string

SUPPORTED_ENTITY_TYPES: list[str] = [EntityTypes.URL, EntityTypes.HOSTNAME, EntityTypes.DOMAIN]


@output_handler
def main() -> None:
    """Build a comprehensive domain dossier combining Iris, RDAP, and WHOIS history."""
    siemplify = SiemplifyAction()
    siemplify.script_name = GET_DOMAIN_PROFILE_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Get Domain Profile Started -----------------")

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
        siemplify, provider_name=INTEGRATION_NAME, param_name="Verify SSL", is_mandatory=True
    )

    status: int = EXECUTION_STATE_COMPLETED
    output_message: str = ""
    result_value: bool = True
    json_results: list[dict[str, Any]] = []
    success_entities: list = []
    failed_entities: list = []
    csv_rows: list[dict] = []

    target_entities = [
        entity
        for entity in siemplify.target_entities
        if entity.entity_type in SUPPORTED_ENTITY_TYPES
    ]

    try:
        dt_manager = DomainToolsManager(
            username=username,
            api_key=api_key,
            verify_ssl=verify_ssl,
            siemplify_logger=siemplify.LOGGER,
        )

        for entity in target_entities:
            domain = extract_domain_from_string(entity.identifier)
            siemplify.LOGGER.info(f"Building profile for: {domain}")

            try:
                iris_models = dt_manager.investigate_domains(domains=[domain])
                iris_model = iris_models[0] if iris_models else None

                rdap_model = dt_manager.get_parsed_domain_rdap(domain=domain)
                whois_model = dt_manager.get_whois_history(domain=domain)

                create_date = iris_model.registration.create_date if iris_model else None
                domain_age_days: int | None = None
                if create_date:
                    try:
                        created = datetime.strptime(create_date[:10], "%Y-%m-%d")
                        domain_age_days = (datetime.now() - created).days
                    except ValueError:
                        pass

                overall_score = iris_model.analytics.overall_risk_score if iris_model else 0
                risk_category = classify_domain_risk(overall_score, domain_age_days)

                profile: dict[str, Any] = {
                    "risk": {
                        "overall_risk_score": overall_score,
                        "proximity_risk_score": iris_model.analytics.proximity_risk_score if iris_model else 0,
                        "threat_profile_risk_score": iris_model.analytics.threat_profile_risk_score.risk_score if iris_model else 0,
                        "malware_risk_score": iris_model.analytics.malware_risk_score if iris_model else 0,
                        "phishing_risk_score": iris_model.analytics.phishing_risk_score if iris_model else 0,
                        "spam_risk_score": iris_model.analytics.spam_risk_score if iris_model else 0,
                        "threats": iris_model.analytics.threat_profile_risk_score.threats if iris_model else [],
                        "evidence": iris_model.analytics.threat_profile_risk_score.evidence if iris_model else [],
                    },
                    "identity": {
                        "registrant_name": iris_model.identity.registrant_name if iris_model else None,
                        "registrant_org": iris_model.identity.registrant_org if iris_model else None,
                        "registrar": iris_model.identity.registrar if iris_model else None,
                        "soa_email": iris_model.identity.soa_email if iris_model else [],
                        "email_domains": iris_model.identity.email_domains if iris_model else [],
                    },
                    "registration": {
                        "create_date": create_date,
                        "expiration_date": iris_model.registration.expiration_date if iris_model else None,
                        "domain_status": iris_model.registration.domain_status if iris_model else False,
                        "registrar_status": iris_model.registration.registrar_status if iris_model else [],
                        "rdap": rdap_model.to_dict() if rdap_model and rdap_model.has_found else {},
                    },
                    "hosting": {
                        "ip_addresses": iris_model.hosting.ip_addresses if iris_model else [],
                        "ip_country_code": iris_model.hosting.ip_country_code if iris_model else "",
                        "name_servers": iris_model.hosting.name_servers if iris_model else [],
                        "mx_servers": iris_model.hosting.mx_servers if iris_model else [],
                        "ssl_certificates": iris_model.hosting.ssl_certificates if iris_model else [],
                    },
                    "history": whois_model.to_dict() if whois_model else {},
                    "metadata": {
                        "last_enriched": datetime.now().strftime("%Y-%m-%d"),
                        "domain_age_days": domain_age_days,
                        "risk_category": risk_category,
                    },
                }

                json_results.append({"Entity": entity.identifier, "EntityResult": profile})
                entity.is_enriched = True
                success_entities.append(entity)

                csv_rows.append({
                    "Domain": domain,
                    "Risk Category": risk_category,
                    "Overall Risk Score": overall_score,
                    "Create Date": create_date or "N/A",
                    "Domain Age (days)": domain_age_days if domain_age_days is not None else "N/A",
                    "Registrant Org": iris_model.identity.registrant_org if iris_model else "N/A",
                    "IP Country": iris_model.hosting.ip_country_code if iris_model else "N/A",
                    "WHOIS Records": whois_model.record_count if whois_model else 0,
                })

            except Exception as e:
                failed_entities.append(entity)
                siemplify.LOGGER.error(f"Failed to build profile for {domain}. Reason: {str(e)}")
                siemplify.LOGGER.exception(e)

        if success_entities:
            siemplify.update_entities(success_entities)
            siemplify.result.add_result_json(json_results)

            output_message = f"Successfully built profiles for {len(success_entities)} domain(s)."

            if csv_rows:
                siemplify.result.add_data_table(
                    "DomainTools Domain Profiles", construct_csv(csv_rows)
                )

            if failed_entities:
                output_message += (
                    f"\nFailed to profile: {', '.join(str(e.identifier) for e in failed_entities)}"
                )
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
    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"Result: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
