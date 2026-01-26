"""
Action script for Domain Tools - Reverse Domain.

Find IPs that point to a particular domain
"""

from __future__ import annotations

from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyUtils import (
    add_prefix_to_dict,
    dict_to_flat,
    flat_dict_to_csv,
    output_handler,
)

from ..core.DomainToolsManager import DomainToolsManager

DOMAINTOOLS_PREFIX = "DT"
SUPPORTED_ENTITY_TYPES: list[str] = [EntityTypes.URL, EntityTypes.HOSTNAME, EntityTypes.DOMAIN]


@output_handler
def main():
    siemplify = SiemplifyAction()
    configuration_settings = siemplify.get_configuration("DomainTools")
    username = configuration_settings["Username"]
    api_key = configuration_settings["ApiToken"]
    verify_ssl = configuration_settings["Verify SSL"]
    domaintools_manager = DomainToolsManager(username, api_key, verify_ssl=verify_ssl)

    output_message = ""
    entities_to_update = []
    json_results = []
    result_value = False

    scope_entities = [
        entity
        for entity in siemplify.target_entities
        if entity.entity_type in SUPPORTED_ENTITY_TYPES
    ]

    for entity in scope_entities:
        extracted_domain = domaintools_manager.extract_domain_from_string(entity.identifier)

        res = domaintools_manager.enrich_domain(extracted_domain)

        if res:
            entities_to_update.append(entity)
            flat_dict_res = dict_to_flat(res)
            csv_res = flat_dict_to_csv(flat_dict_res)
            entity.additional_properties.update(
                add_prefix_to_dict(flat_dict_res, DOMAINTOOLS_PREFIX)
            )
            siemplify.result.add_entity_table(entity.identifier, csv_res)
            result_value = True

            json_results.append({"Entity": entity.identifier, "EntityResult": res})

        else:
            pass

    siemplify.update_entities(entities_to_update)

    if json_results:
        siemplify.result.add_result_json(json_results)

    if entities_to_update:
        output_message = f"{', '.join(map(str, entities_to_update))} : enriched by DomainTools."
    else:
        output_message = "No entities were enriched."

    siemplify.end(output_message, result_value)


if __name__ == "__main__":
    main()
