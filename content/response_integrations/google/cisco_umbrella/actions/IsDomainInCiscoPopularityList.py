from __future__ import annotations
from dataclasses import asdict

from cisco_umbrella.core.CiscoUmbrellaStaticResourcesManager import (
    CiscoUmbrellaStaticResourcesManager,
    OrderedDomain,
    StaticAssets,
)
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyDataModel import EntityTypes, DomainEntityInfo
from soar_sdk.SiemplifyUtils import add_prefix_to_dict_keys, output_handler
from cisco_umbrella.core.utils import get_hostname

CISCO_UMBRELLA_PREFIX = "CU"
INTEGRATION_NAME = "CiscoUmbrella"
SCRIPT_NAME = f"{INTEGRATION_NAME} - Is Domain In Cisco Popularity List"
SUCCESS_MESSAGE = (
    "Successfully returned information about the following entities"
    " in Cisco Umbrella: {entities}"
)
SUPPORTED_ENTITIES = [EntityTypes.HOSTNAME, EntityTypes.URL, EntityTypes.DOMAIN]


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = SCRIPT_NAME
    siemplify.LOGGER.info("================= Main - Param Init =================")
    output_message = ""
    result_value = True
    successful_entities = []
    status = EXECUTION_STATE_COMPLETED
    scope_entities = [
        entity
        for entity in siemplify.target_entities
        if entity.entity_type in SUPPORTED_ENTITIES
    ]
    entity_result_registry = {
        _normalize_entity(entity): _Result(entity) for entity in scope_entities
    }

    try:
        manager = CiscoUmbrellaStaticResourcesManager()
        siemplify.LOGGER.info("----------------- Main - Started -----------------")

        top_domains = {
            ordered_domain.domain: ordered_domain
            for ordered_domain in manager.get_asset(StaticAssets.TOP_1M_CSV_ZIP)
        }
        for entity_identifier, result in entity_result_registry.items():
            if entity_identifier in top_domains:
                result.add_found(top_domains[entity_identifier])
                successful_entities.append(result.entity.identifier)

        siemplify.LOGGER.info("Enriching entities")
        siemplify.update_entities(
            [result.enrich() for result in entity_result_registry.values()]
        )

        siemplify.LOGGER.info("Constructing json results")
        json_results = [result.as_dict() for result in entity_result_registry.values()]
        siemplify.result.add_result_json(json_results)
        if successful_entities:
            output_message = SUCCESS_MESSAGE.format(
                entities=",\n".join(set(successful_entities))
            )
    except Exception as e:  # pylint: disable=broad-exception-caught
        output_message = f"Error executing action '{SCRIPT_NAME}'. Reason: {e}"
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        result_value = False

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"Result Value: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")

    siemplify.end(output_message, result_value, status)


def _normalize_entity(entity: DomainEntityInfo) -> str:
    normalized = str(entity.identifier).lower().strip()
    if entity.entity_type == EntityTypes.URL:
        normalized = get_hostname(normalized)
    return normalized


class _Result:
    def __init__(self, entity: DomainEntityInfo) -> None:
        self.entity = entity
        self.entries: list[OrderedDomain] = []

    def add_found(self, domain: OrderedDomain):
        self.entries.append(domain)

    def is_found(self) -> bool:
        return bool(self.entries)

    def enrich(self) -> DomainEntityInfo:
        """
        Enrich and return attached entity
        Returns: attached entity

        """
        self.entity.additional_properties.update(
            add_prefix_to_dict_keys(
                {"is_found_in_cisco_popular_list": self.is_found()},
                CISCO_UMBRELLA_PREFIX,
            )
        )
        self.entity.is_enriched = True
        return self.entity

    def as_dict(self) -> dict:
        return {
            "Entity": self.entity.identifier,
            "EntityResult": {
                "found": self.is_found(),
                "entries": [asdict(entry) for entry in self.entries],
            },
        }


if __name__ == "__main__":
    main()
