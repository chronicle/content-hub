"""
Action script for DomainTools - Get Domain Risk.

Enrich external domain entity with the domain risk score and detailed risk
profile data from DomainTools.
"""

from __future__ import annotations

from typing import Any

from soar_sdk.SiemplifyAction import SiemplifyAction  # type: ignore[import-not-found]
from soar_sdk.SiemplifyDataModel import EntityTypes  # type: ignore[import-not-found]
from soar_sdk.SiemplifyUtils import output_handler  # type: ignore[import-not-found]

from ..core.DomainToolsManager import DomainToolsManager
from ..core.exceptions import (
    DomainToolsApiError,
    DomainToolsLicenseError,
    DomainToolsManagerError,
)

RISK_SCORE_KEY: str = "risk_score"
SUPPORTED_ENTITY_TYPES: list[str] = [EntityTypes.URL, EntityTypes.HOSTNAME, EntityTypes.DOMAIN]


@output_handler
def main() -> None:
    """Get domain risk score and data for external domain/URL entities."""
    siemplify = SiemplifyAction()

    siemplify.LOGGER.info("---------------- Main - Param Init ----------------")

    conf = siemplify.get_configuration("DomainTools")
    username = conf.get("Username")
    api_key = conf.get("ApiToken")
    verify_ssl = conf.get("Verify SSL", "False").lower() == "true"

    try:
        threshold = float(siemplify.parameters.get("Threshold"))
    except (ValueError, TypeError):
        siemplify.end(
            "Invalid value provided for 'Threshold'. Please provide a number.",
            False,
        )
        return

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    try:
        dt_manager = DomainToolsManager(username=username, api_key=api_key, verify_ssl=verify_ssl)
    except DomainToolsLicenseError as e:
        siemplify.end(f"Failed to create manager: {e}", False)
        return

    enriched_entities: list[Any] = []
    risky_domains: list[str] = []
    json_results: list[dict[str, Any]] = []
    is_risky: bool = False
    output_message: str = ""

    target_entities = [
        entity
        for entity in siemplify.target_entities
        if entity.entity_type in SUPPORTED_ENTITY_TYPES
    ]

    for entity in target_entities:
        siemplify.LOGGER.info(f"Processing entity: {entity.identifier}")
        domain = dt_manager.extract_domain_from_string(entity.identifier)

        try:
            risk_data = dt_manager.get_domain_risk_data(domain)
            if not risk_data:
                siemplify.LOGGER.info(f"No risk data found for {domain}")
                continue

            entity_result_data = dt_manager.format_risk_entity_result(domain, risk_data)

            json_results.append({"Entity": entity.identifier, "EntityResult": entity_result_data})

            risk_score_value = entity_result_data.get(RISK_SCORE_KEY)

            if risk_score_value is not None:
                entity.additional_properties["DT_Risk"] = str(risk_score_value)

                try:
                    if float(risk_score_value) > threshold:
                        is_risky = True
                        entity.is_suspicious = True
                        risky_domains.append(entity.identifier)
                        siemplify.LOGGER.info(
                            f"Entity {entity.identifier} marked as suspicious (Score: "
                            f"{risk_score_value} > Threshold: {threshold})"
                        )
                except (ValueError, TypeError) as e:
                    siemplify.LOGGER.error(
                        f"Could not parse risk score for {domain}: {risk_score_value}. Error: {e}"
                    )

            enriched_entities.append(entity)

        except (DomainToolsApiError, DomainToolsLicenseError) as e:
            siemplify.LOGGER.error(f"An error occurred for {domain}: {e}")
        except DomainToolsManagerError as e:
            siemplify.LOGGER.error(f"An unexpected error occurred for {domain}: {e}")
            siemplify.LOGGER.exception(e)

    if enriched_entities:
        siemplify.update_entities(enriched_entities)
        siemplify.result.add_result_json(json_results)
        output_message = f"Successfully enriched {len(enriched_entities)} entities."

    if risky_domains:
        output_message += (
            "\nFollowing domains were found to be risky by DomainTools:\n"
            f"{', '.join(risky_domains)}"
        )
    elif not enriched_entities:
        output_message = "No entities were enriched."
    else:
        output_message += "\nNo risky domains were found."

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.end(output_message.strip(), is_risky)


if __name__ == "__main__":
    main()
