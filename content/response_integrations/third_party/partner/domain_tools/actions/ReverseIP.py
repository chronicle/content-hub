"""
Action script for Domain Tools - Reverse IP.

Find domain names that share a particular IP address
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

# Imports
from ..core.DomainToolsManager import DomainToolsManager

# Consts
DOMAINTOOLS_PREFIX = "DT"
ADDRESS = EntityTypes.ADDRESS


@output_handler
def main():

    # Configurations
    siemplify = SiemplifyAction()
    configuration_settings = siemplify.get_configuration("DomainTools")
    username = configuration_settings["Username"]
    api_key = configuration_settings["ApiToken"]
    verify_ssl = configuration_settings["Verify SSL"]
    domaintools_manager = DomainToolsManager(username, api_key, verify_ssl=verify_ssl)

    # Variables Definition.
    output_message = ""
    entities_to_update = []
    result_value = False

    #  Get scope entities.
    scope_entities = [
        entity
        for entity in siemplify.target_entities
        if entity.entity_type == ADDRESS and not entity.is_internal
    ]

    for entity in scope_entities:
        # Get response
        res = domaintools_manager.get_domains_by_ip(entity.identifier)

        if res:
            # Push entity to entities to update array.
            entities_to_update.append(entity)
            # Convert response dict to flat dict.
            flat_dict_res = dict_to_flat(res)
            # Convert response to CSV format string list.
            csv_res = flat_dict_to_csv(flat_dict_res)
            # Enrich Entity.
            entity.additional_properties.update(
                add_prefix_to_dict(flat_dict_res, DOMAINTOOLS_PREFIX)
            )
            # Print table to result action view.
            siemplify.result.add_entity_table(entity.identifier, csv_res)
            # Return true on action result.
            result_value = True
        else:
            pass

    # Update Entities.
    siemplify.update_entities(entities_to_update)

    # Organize output message.
    if entities_to_update:
        output_message = f"{', '.join(map(str, entities_to_update))} : enriched by DomainTools."
    else:
        output_message = "No entities were enriched."

    # End action
    siemplify.end(output_message, result_value)


if __name__ == "__main__":
    main()
