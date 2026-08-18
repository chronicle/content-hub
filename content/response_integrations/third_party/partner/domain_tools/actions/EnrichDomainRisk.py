"""
Action script for DomainTools - Enrich Domain Risk.

Enriches domain entities with risk scores and classifies them into risk categories
(high_risk, medium_risk, suspicious, young_domain, low_risk).
"""

from __future__ import annotations

from typing import Any

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyUtils import output_handler
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


@output_handler
def main() -> None:
    """Enrich domain entities with DomainTools risk scores and classification."""
    siemplify = SiemplifyAction()
    siemplify.script_name = ENRICH_DOMAIN_RISK_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Enrich Domain Risk Started -----------------")

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
    risk_threshold: int = int(
        extract_action_param(
            siemplify, param_name="Risk Threshold", default_value=str(RISK_SCORE_HIGH), print_value=True
        )
    )

    status: int = EXECUTION_STATE_COMPLETED
    output_message: str = ""
    result_value: bool = True
    json_results: list[dict[str, Any]] = []
    success_entities: list = []
    failed_entities: list = []

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

        extracted_domains: dict[str, Any] = {
            domain: entity
            for entity in target_entities
            if (domain := extract_domain_from_string(entity.identifier))
        }

        if not extracted_domains:
            output_message = "No domain entities found to enrich."
            result_value = False
            siemplify.end(output_message, result_value, status)
            return

        enriched_results = dt_manager.enrich_domains_with_risk(list(extracted_domains.keys()))

        for enriched in enriched_results:
            entity = extracted_domains.get(enriched.domain)
            if not entity:
                continue
            try:
                enriched_dict = enriched.to_dict()
                json_results.append({"Entity": entity.identifier, "EntityResult": enriched_dict})

                flattened = dict_to_flat(enriched_dict)
                prefixed = add_prefix_to_dict_keys(flattened, "DT")
                entity.additional_properties.update(prefixed)

                entity.is_enriched = True
                if enriched.overall_risk_score >= risk_threshold or enriched.is_young_domain:
                    entity.is_suspicious = True

                success_entities.append(entity)
            except Exception as e:
                failed_entities.append(entity)
                siemplify.LOGGER.error(
                    f"Unable to enrich entity: {entity.identifier}. Reason: {str(e)}"
                )
                siemplify.LOGGER.exception(e)

        if success_entities:
            siemplify.update_entities(success_entities)
            siemplify.result.add_result_json(json_results)
            csv_table_results = [
                enriched.to_table_data()
                for enriched in enriched_results
                if extracted_domains.get(enriched.domain) in success_entities
            ]
            if csv_table_results:
                siemplify.result.add_data_table(
                    "Domain Risk Enrichment", construct_csv(csv_table_results)
                )

            suspicious_count = sum(
                1 for e in success_entities if e.is_suspicious
            )
            output_message = (
                f"Successfully enriched {len(success_entities)} domain(s). "
                f"{suspicious_count} marked as suspicious."
            )

            if failed_entities:
                output_message += (
                    f"\nFailed to enrich: {', '.join(str(e.identifier) for e in failed_entities)}"
                )
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
    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"Result: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
