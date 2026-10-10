"""
Action script for DomainTools - Bulk Enrich Domains.

Batch-enriches up to 100 domains and returns aggregate statistics
by risk category, plus per-domain enrichment details.
"""

from __future__ import annotations

from typing import Any

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyUtils import output_handler
from TIPCommon.extraction import extract_action_param, extract_configuration_param
from TIPCommon.transformation import construct_csv

from ..core.constants import (
    BULK_ENRICH_DOMAINS_SCRIPT_NAME,
    BULK_ENRICH_MAX_DOMAINS,
    INTEGRATION_NAME,
    RISK_CATEGORY_HIGH,
    RISK_CATEGORY_MEDIUM,
    RISK_CATEGORY_SUSPICIOUS,
    RISK_CATEGORY_YOUNG,
)
from ..core.DomainToolsManager import DomainToolsManager
from ..core.UtilsManager import extract_domain_from_string

SUPPORTED_ENTITY_TYPES: list[str] = [EntityTypes.URL, EntityTypes.HOSTNAME, EntityTypes.DOMAIN]


@output_handler
def main() -> None:
    """Batch-enrich domains and return aggregate risk category statistics."""
    siemplify = SiemplifyAction()
    siemplify.script_name = BULK_ENRICH_DOMAINS_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Bulk Enrich Domains Started -----------------")

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
    domains_param: str = extract_action_param(
        siemplify, param_name="Domains", default_value="", print_value=True
    )
    include_young: bool = extract_action_param(
        siemplify, param_name="Include Young Domains", input_type=bool, default_value=True
    )
    merge_with_entities: bool = extract_action_param(
        siemplify, param_name="Merge With Case Entities", input_type=bool, default_value=False
    )

    status: int = EXECUTION_STATE_COMPLETED
    output_message: str = ""
    result_value: bool = True

    try:
        dt_manager = DomainToolsManager(
            username=username,
            api_key=api_key,
            verify_ssl=verify_ssl,
            siemplify_logger=siemplify.LOGGER,
        )

        manual = [d.strip() for d in domains_param.split(",") if d.strip()] if domains_param else []
        entity_domains = [
            domain
            for entity in siemplify.target_entities
            if entity.entity_type in SUPPORTED_ENTITY_TYPES
            if (domain := extract_domain_from_string(entity.identifier))
        ]

        if manual and merge_with_entities:
            domains = list(dict.fromkeys(manual + entity_domains))
        elif manual:
            domains = manual
        else:
            domains = list(dict.fromkeys(entity_domains))

        if not domains:
            output_message = "No domains provided or found in scope."
            result_value = False
            siemplify.end(output_message, result_value, status)
            return

        if len(domains) > BULK_ENRICH_MAX_DOMAINS:
            siemplify.LOGGER.warn(
                f"Domain count {len(domains)} exceeds max {BULK_ENRICH_MAX_DOMAINS}. Truncating."
            )
            domains = domains[:BULK_ENRICH_MAX_DOMAINS]

        enriched_results = dt_manager.enrich_domains_with_risk(domains)

        enriched_domain_set = {e.domain for e in enriched_results}
        missing_domains = [d for d in domains if d not in enriched_domain_set]

        summary: dict[str, Any] = {
            "total_domains": len(enriched_results),
            "high_risk_count": 0,
            "medium_risk_count": 0,
            "suspicious_count": 0,
            "young_domain_count": 0,
            "low_risk_count": 0,
            "missing_count": len(missing_domains),
        }
        if missing_domains:
            summary["missing_domains"] = missing_domains
        domains_output: list[dict[str, Any]] = []

        for enriched in enriched_results:
            if enriched.risk_category == RISK_CATEGORY_HIGH:
                summary["high_risk_count"] += 1
            elif enriched.risk_category == RISK_CATEGORY_MEDIUM:
                summary["medium_risk_count"] += 1
            elif enriched.risk_category == RISK_CATEGORY_SUSPICIOUS:
                summary["suspicious_count"] += 1
            elif enriched.risk_category == RISK_CATEGORY_YOUNG:
                summary["young_domain_count"] += 1
            else:
                summary["low_risk_count"] += 1

            if not include_young and enriched.risk_category == RISK_CATEGORY_YOUNG:
                continue

            domains_output.append(enriched.to_dict())

        json_result = [{"Entity": "BulkEnrichment", "EntityResult": {"summary": summary, "domains": domains_output}}]
        siemplify.result.add_result_json(json_result)

        csv_rows = [enriched.to_table_data() for enriched in enriched_results]
        if csv_rows:
            siemplify.result.add_data_table("Bulk Domain Enrichment", construct_csv(csv_rows))

        output_message = (
            f"Enriched {summary['total_domains']} domain(s): "
            f"{summary['high_risk_count']} high risk, "
            f"{summary['medium_risk_count']} medium risk, "
            f"{summary['suspicious_count']} suspicious, "
            f"{summary['young_domain_count']} young domains, "
            f"{summary['low_risk_count']} low risk."
        )
        if missing_domains:
            output_message += (
                f"\nNot returned by API ({len(missing_domains)}): {', '.join(missing_domains)}"
            )

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
