"""
Action script for Domain Tools - Get Hosting History.

Get domain hosting history information, enrich and add CSV table
"""

from __future__ import annotations

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

URL = EntityTypes.URL
HOST = EntityTypes.HOSTNAME


@output_handler
def main():
    siemplify = SiemplifyAction()
    conf = siemplify.get_configuration("DomainTools")
    username = conf["Username"]
    key = conf["ApiToken"]
    verify_ssl = conf["Verify SSL"]
    dt_manager = DomainToolsManager(username, key, verify_ssl=verify_ssl)

    entities = [
        entity
        for entity in siemplify.target_entities
        if (entity.entity_type == URL or entity.entity_type == HOST)
    ]
    enriched_entities = []
    is_risky = False
    output_message = "No Risky domain were found"
    domain_hosting_history = None
    for entity in entities:
        # Remove '@' or http
        domain = dt_manager.extract_domain_from_string(entity.identifier)
        print(domain)
        try:
            domain_hosting_history = dt_manager.get_hosting_history(domain)
            print(domain_hosting_history)
            if domain_hosting_history:
                # Flat the dict
                domain_hosting_history = dict_to_flat(domain_hosting_history)
                csv_output = flat_dict_to_csv(domain_hosting_history)
                # Add prefix to dict
                domain_hosting_history = add_prefix_to_dict_keys(domain_hosting_history, "DT")
                siemplify.result.add_entity_table(entity.identifier, csv_output)
                entity.additional_properties.update(domain_hosting_history)
                enriched_entities.append(entity)
        except DomainToolsManagerError:
            continue

    if domain_hosting_history:
        output_message = "Domains Hosting History attached to results"
    siemplify.end(output_message, is_risky)


if __name__ == "__main__":
    main()
