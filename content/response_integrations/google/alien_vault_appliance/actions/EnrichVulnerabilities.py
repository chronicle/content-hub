from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import (
    dict_to_flat,
    add_prefix_to_dict,
    convert_dict_to_json_result_dict,
)
from ..core.AlienVaultManager import AlienVaultManager


@output_handler
def main():
    siemplify = SiemplifyAction()
    configurations = siemplify.get_configuration("AlienVaultAppliance")
    server_address = configurations["Api Root"]
    username = configurations["Username"]
    password = configurations["Password"]

    alienvault_manager = AlienVaultManager(server_address, username, password)

    enriched_entities = []
    json_result = {}

    for entity in siemplify.target_entities:
        asset_id = None

        if entity.entity_type == EntityTypes.ADDRESS:
            asset_id = alienvault_manager.get_asset_id_by_ip(entity.identifier)

        elif entity.entity_type == EntityTypes.HOSTNAME:
            asset_id = alienvault_manager.get_asset_id_by_hostname(entity.identifier)

        if asset_id:
            vulnerabilities = alienvault_manager.get_asset_vulnerabilities(asset_id)

            if vulnerabilities:
                json_result[entity.identifier] = vulnerabilities
                # Enrich the entity with the found vulnerabilities
                for count, vulnerability in enumerate(vulnerabilities):
                    # Flatten the vulnerability
                    flat_vulnerability = dict_to_flat(vulnerability)
                    # Add prefixes to vulnerability
                    flat_vulnerability = add_prefix_to_dict(
                        flat_vulnerability, str(count)
                    )
                    flat_vulnerability = add_prefix_to_dict(
                        flat_vulnerability, "AlientVault_Vulnerabilities"
                    )
                    # Entich the entity with the vulnerability
                    entity.additional_properties.update(flat_vulnerability)

                # Attach vulnerabilities as csv as well
                csv_output = alienvault_manager.construct_csv(vulnerabilities)
                siemplify.result.add_entity_table(entity.identifier, csv_output)

                enriched_entities.append(entity)

    siemplify.result.add_result_json(convert_dict_to_json_result_dict(json_result))

    if enriched_entities:
        entities_names = [entity.identifier for entity in enriched_entities]

        output_message = (
            "The following entities were enriched by AlienVault:\n"
            + "\n".join(entities_names)
        )

        siemplify.update_entities(enriched_entities)

        siemplify.end(output_message, "true")

    else:
        output_message = "No entities were enriched."
        # No entities found and action is completed
        siemplify.end(output_message, "false")


if __name__ == "__main__":
    main()
