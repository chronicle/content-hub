"""
Action script for Domain Tools - Get Domain Profile.

Enrich external domain entity with DomainTools threat Intelligence data
and return CSV output, including JSON results.
"""

from __future__ import annotations

from typing import Any

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyUtils import (
    add_prefix_to_dict_keys,
    dict_to_flat,
    flat_dict_to_csv,
    output_handler,
)

from ..core.DomainToolsManager import DomainToolsManager
from ..core.exceptions import DomainToolsManagerError

SUPPORTED_ENTITY_TYPES: list[str] = [EntityTypes.URL, EntityTypes.HOSTNAME, EntityTypes.DOMAIN]


def process_entity(
    siemplify: SiemplifyAction,
    dt_manager: DomainToolsManager,
    entity: Any,
) -> dict[str, Any] | None:
    """
    Processes a single entity to retrieve its Domain Profile, enrich it,
    add a CSV table, and return the raw profile data for JSON results.

    Args:
        siemplify (SiemplifyAction): Siemplify API client.
        dt_manager (DomainToolsManager): Initialized DomainTools manager.
        entity (Any): The entity object to process.

    Returns:
        dict[str, Any] | None: The raw domain profile data if successful,
                               otherwise None.
    """
    domain: str = dt_manager.extract_domain_from_string(entity.identifier)
    siemplify.LOGGER.info(f"Processing entity: {entity.identifier}")

    try:
        domain_profile: dict[str, Any] | None = dt_manager.get_domain_profile(domain)
    except DomainToolsManagerError:
        siemplify.LOGGER.error(
            f"Failed to get domain profile for {domain}. Skipping entity.",
            exc_info=True,
        )
        return None

    if domain_profile:
        flattened_profile: dict[str, Any] = dict_to_flat(domain_profile)
        csv_output: str = flat_dict_to_csv(flattened_profile)
        siemplify.result.add_entity_table(entity.identifier, csv_output)

        prefixed_profile: dict[str, Any] = add_prefix_to_dict_keys(flattened_profile, "DT")
        entity.additional_properties.update(prefixed_profile)
        entity.is_enriched = True

        siemplify.LOGGER.info(f"Successfully enriched {entity.identifier}")
        return domain_profile

    siemplify.LOGGER.info(f"No domain profile found for {domain}")
    return None


@output_handler
def main() -> None:
    """Enrich external domain entity with DomainTools threat Intelligence data."""
    siemplify = SiemplifyAction()

    siemplify.LOGGER.info("Reading configuration from Server")
    conf = siemplify.get_configuration("DomainTools")
    username: str = conf.get("Username")
    api_key: str = conf.get("ApiToken")
    verify_ssl: str = conf.get("Verify SSL", "False")

    siemplify.LOGGER.info(f"Username: {username}")
    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    enriched_entities: list[Any] = []
    json_results: list[dict[str, Any]] = []
    result_value: str = "false"
    status: int = EXECUTION_STATE_COMPLETED
    output_message: str = ""

    try:
        dt_manager = DomainToolsManager(
            username=username,
            api_key=api_key,
            verify_ssl=verify_ssl,
        )

        target_entities: list[Any] = [
            entity
            for entity in siemplify.target_entities
            if entity.entity_type in SUPPORTED_ENTITY_TYPES
        ]

        for entity in target_entities:
            profile_data = process_entity(siemplify, dt_manager, entity)

            if profile_data:
                enriched_entities.append(entity)
                json_results.append({"Entity": entity.identifier, "EntityResult": profile_data})

        if enriched_entities:
            siemplify.update_entities(enriched_entities)
            siemplify.result.add_result_json(json_results)

            output_message = "Entities Enriched By Domain Tools:\n{0}".format(
                "\n".join(map(str, enriched_entities))
            )
            result_value = "true"
        else:
            output_message = "No entities were enriched."
            result_value = "false"

    except Exception as err:
        output_message = f"Error running action error is: {str(err)}"
        status = EXECUTION_STATE_FAILED
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(err)
        result_value = "false"

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  result_value: {result_value}\n  output_message: {output_message}"
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
