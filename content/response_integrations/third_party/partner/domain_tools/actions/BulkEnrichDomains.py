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


def _extract_params(siemplify: SiemplifyAction) -> tuple:
    """Extract integration configuration and action parameters from the SOAR context."""
    username = extract_configuration_param(
        siemplify, provider_name=INTEGRATION_NAME, param_name="Username",
        is_mandatory=True, print_value=True,
    )
    api_key = extract_configuration_param(
        siemplify, provider_name=INTEGRATION_NAME, param_name="ApiToken",
        is_mandatory=True, print_value=True,
    )
    verify_ssl = extract_configuration_param(
        siemplify, provider_name=INTEGRATION_NAME, param_name="Verify SSL", is_mandatory=True
    )
    domains_param = extract_action_param(siemplify, "Domains", print_value=True)
    include_young = extract_action_param(
        siemplify, param_name="Include Young Domains", input_type=bool, default_value=True
    )
    merge_with_entities = extract_action_param(
        siemplify, param_name="Merge With Case Entities", input_type=bool, default_value=False
    )
    return username, api_key, verify_ssl, domains_param, include_young, merge_with_entities


def _collect_domains(
    siemplify: SiemplifyAction, domains_param: str | None, merge_with_entities: bool
) -> list[str]:
    """Build the deduplicated domain list from manual input, case entities, or both."""
    manual = [d.strip() for d in domains_param.split(",") if d.strip()] if domains_param else []
    entity_domains = [
        domain
        for entity in siemplify.target_entities
        if entity.entity_type in SUPPORTED_ENTITY_TYPES
        if (domain := extract_domain_from_string(entity.identifier))
    ]
    if manual and merge_with_entities:
        return list(dict.fromkeys(manual + entity_domains))
    return manual if manual else list(dict.fromkeys(entity_domains))


def _enrich_and_summarize(
    dt_manager: DomainToolsManager, domains: list[str]
) -> tuple[list, dict[str, Any], list[str]]:
    """Enrich domains via the API and return results, a risk category summary, and any missing domains."""
    enriched_results = dt_manager.enrich_domains_with_risk(domains)
    missing_domains = [d for d in domains if d not in {e.domain for e in enriched_results}]
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
    return enriched_results, summary, missing_domains


def _write_results(
    siemplify: SiemplifyAction,
    enriched_results: list,
    include_young: bool,
    summary: dict[str, Any],
) -> None:
    """Write JSON result and CSV data table to the SOAR case."""
    domains_output = [
        e.to_dict() for e in enriched_results
        if include_young or e.risk_category != RISK_CATEGORY_YOUNG
    ]
    json_result = [{"Entity": "BulkEnrichment", "EntityResult": {"summary": summary, "domains": domains_output}}]
    siemplify.result.add_result_json(json_result)
    csv_rows = [e.to_table_data() for e in enriched_results]
    if csv_rows:
        siemplify.result.add_data_table("Bulk Domain Enrichment", construct_csv(csv_rows))


def _format_output_message(summary: dict[str, Any], missing_domains: list[str]) -> str:
    """Format the action output message with risk category counts and any missing domains."""
    msg = (
        f"Enriched {summary['total_domains']} domain(s): "
        f"{summary['high_risk_count']} high risk, "
        f"{summary['medium_risk_count']} medium risk, "
        f"{summary['suspicious_count']} suspicious, "
        f"{summary['young_domain_count']} young domains, "
        f"{summary['low_risk_count']} low risk."
    )
    if missing_domains:
        msg += f"\nNot returned by API ({len(missing_domains)}): {', '.join(missing_domains)}"
    return msg


@output_handler
def main() -> None:
    siemplify = SiemplifyAction()
    siemplify.script_name = BULK_ENRICH_DOMAINS_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Bulk Enrich Domains Started -----------------")

    username, api_key, verify_ssl, domains_param, include_young, merge_with_entities = _extract_params(siemplify)

    status: int = EXECUTION_STATE_COMPLETED
    output_message: str = ""
    result_value: bool = True

    try:
        dt_manager = DomainToolsManager(
            username=username, api_key=api_key, verify_ssl=verify_ssl,
            siemplify_logger=siemplify.LOGGER,
        )

        domains = _collect_domains(siemplify, domains_param, merge_with_entities)
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

        enriched_results, summary, missing_domains = _enrich_and_summarize(dt_manager, domains)
        _write_results(siemplify, enriched_results, include_young, summary)
        output_message = _format_output_message(summary, missing_domains)

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
