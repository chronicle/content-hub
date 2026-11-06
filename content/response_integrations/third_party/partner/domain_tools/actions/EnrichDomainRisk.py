"""
Action script for DomainTools - Enrich Domain Risk.

Enriches domain entities with risk scores and classifies them into risk categories
(high_risk, medium_risk, suspicious, young_domain, low_risk).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyUtils import output_handler

if TYPE_CHECKING:
    from soar_sdk.SiemplifyDataModel import DomainEntityInfo
from TIPCommon.extraction import extract_action_param, extract_configuration_param
from TIPCommon.transformation import add_prefix_to_dict_keys, construct_csv, dict_to_flat

from ..core.constants import (
    ENRICH_DOMAIN_RISK_SCRIPT_NAME,
    INTEGRATION_NAME,
    RISK_SCORE_HIGH,
)
from ..core.DomainToolsManager import DomainToolsManager
from ..core.UtilsManager import extract_domain_from_string

SUPPORTED_ENTITY_TYPES: list[str] = [EntityTypes.URL, EntityTypes.HOSTNAME, EntityTypes.DOMAIN]


def _extract_params(siemplify: SiemplifyAction) -> tuple:
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
    risk_threshold = extract_action_param(
        siemplify,
        "Risk Threshold",
        default_value=RISK_SCORE_HIGH,
        input_type=int,
        print_value=True,
    )
    return username, api_key, verify_ssl, risk_threshold


def _extract_unique_domains(siemplify: SiemplifyAction) -> dict[str, list[DomainEntityInfo]]:
    """Return a domain→entities mapping; multiple entities can share the same root domain."""
    result: dict[str, list[DomainEntityInfo]] = {}
    for entity in siemplify.target_entities:
        if entity.entity_type not in SUPPORTED_ENTITY_TYPES:
            continue
        if domain := extract_domain_from_string(entity.identifier):
            result.setdefault(domain, []).append(entity)
    return result


def _enrich_and_mark_entities(
    dt_manager: DomainToolsManager,
    extracted_domains: dict[str, list[DomainEntityInfo]],
    risk_threshold: int,
    logger: Any,
) -> tuple[list, list, list, list[str], list[dict[str, Any]]]:
    enriched_results = dt_manager.enrich_domains_with_risk(list(extracted_domains.keys()))
    success_entities: list = []
    failed_entities: list = []
    json_results: list[dict[str, Any]] = []
    for enriched in enriched_results:
        entities = extracted_domains.get(enriched.domain)
        if not entities:
            continue
        enriched_dict = enriched.to_dict()
        prefixed = add_prefix_to_dict_keys(dict_to_flat(enriched_dict), "DT")
        is_suspicious = enriched.overall_risk_score >= risk_threshold or enriched.is_young_domain
        enriched.is_suspicious = is_suspicious
        for entity in entities:
            try:
                json_results.append({"Entity": entity.identifier, "EntityResult": enriched_dict})
                entity.additional_properties.update(prefixed)
                entity.is_enriched = True
                entity.is_suspicious = is_suspicious
                success_entities.append(entity)
            except Exception as e:
                failed_entities.append(entity)
                logger.error(f"Unable to enrich entity: {entity.identifier}. Reason: {str(e)}")
                logger.exception(e)
    missing_domains = [d for d in extracted_domains if d not in {e.domain for e in enriched_results}]
    return enriched_results, success_entities, failed_entities, missing_domains, json_results


def _write_results(
    siemplify: SiemplifyAction,
    enriched_results: list,
    extracted_domains: dict[str, list[DomainEntityInfo]],
    success_entities: list,
    missing_domains: list[str],
    json_results: list[dict[str, Any]],
) -> None:
    siemplify.update_entities(success_entities)
    if missing_domains:
        json_results.append({"Entity": "MissingDomains", "EntityResult": {"missing_domains": missing_domains}})
    siemplify.result.add_result_json(json_results)
    success_set = set(id(e) for e in success_entities)
    csv_rows = [
        enriched.to_table_data()
        for enriched in enriched_results
        if any(id(e) in success_set for e in extracted_domains.get(enriched.domain, []))
    ]
    if csv_rows:
        siemplify.result.add_data_table("Domain Risk Enrichment", construct_csv(csv_rows))


def _build_summary_message(
    success_entities: list,
    risk_threshold: int,
    failed_entities: list,
    missing_domains: list[str],
) -> str:
    suspicious_count = sum(1 for e in success_entities if e.is_suspicious)
    msg = (
        f"Successfully enriched {len(success_entities)} domain(s). "
        f"{suspicious_count} marked as suspicious based on the given threshold of {risk_threshold}. \n"
    )
    if failed_entities:
        msg += f"\nFailed to enrich: {', '.join(str(e.identifier) for e in failed_entities)}"
    if missing_domains:
        msg += f"\nNot returned by API: {', '.join(missing_domains)}"
    return msg


@output_handler
def main() -> None:
    siemplify = SiemplifyAction()
    siemplify.script_name = ENRICH_DOMAIN_RISK_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Enrich Domain Risk Started -----------------")

    username, api_key, verify_ssl, risk_threshold = _extract_params(siemplify)

    status: int = EXECUTION_STATE_COMPLETED
    output_message: str = ""
    result_value: bool = True

    try:
        dt_manager = DomainToolsManager(
            username=username, api_key=api_key, verify_ssl=verify_ssl,
            siemplify_logger=siemplify.LOGGER,
        )

        extracted_domains = _extract_unique_domains(siemplify)
        if not extracted_domains:
            output_message = "No domain entities found to enrich."
            result_value = False
            siemplify.end(output_message, result_value, status)
            return

        enriched_results, success_entities, failed_entities, missing_domains, json_results = (
            _enrich_and_mark_entities(dt_manager, extracted_domains, risk_threshold, siemplify.LOGGER)
        )

        if success_entities:
            _write_results(siemplify, enriched_results, extracted_domains, success_entities, missing_domains, json_results)
            output_message = _build_summary_message(success_entities, risk_threshold, failed_entities, missing_domains)
        else:
            output_message = "No entities were enriched."
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
