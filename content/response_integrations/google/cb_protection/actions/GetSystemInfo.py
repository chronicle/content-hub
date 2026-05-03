from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import (
    dict_to_flat,
    add_prefix_to_dict,
    flat_dict_to_csv,
    convert_dict_to_json_result_dict,
)
from ..core.CarbonBlackProtectionManager import CBProtectionManager


@output_handler
def main():
    siemplify = SiemplifyAction()
    configurations = siemplify.get_configuration("CBProtection")
    server_addr = configurations["Api Root"]
    api_key = configurations["Api Key"]

    cb_protection = CBProtectionManager(server_addr, api_key)

    enriched_entities = []
    json_result = {}
    errors = ""

    for entity in siemplify.target_entities:
        try:
            computer_obj = None

            if entity.entity_type == EntityTypes.ADDRESS:
                computer_obj = cb_protection.get_computer_by_ip(entity.identifier)

            elif entity.entity_type == EntityTypes.HOSTNAME:
                computer_obj = cb_protection.get_computer_by_hostname(entity.identifier)

            if computer_obj:
                # Enrich the entity with the data
                computer = computer_obj.original_document
                flat_computer = dict_to_flat(computer)
                flat_computer = add_prefix_to_dict(flat_computer, "CBProtection")
                entity.additional_properties.update(flat_computer)
                entity.is_enriched = True

                # CR: Move to manager
                computer_info = {
                    "Id": computer.get("id"),
                    "Hostname": computer.get("name"),
                    "Mac Address": computer.get("macAddress"),
                    "Ip Address": computer.get("ipAddress"),
                    "Policy Name": computer.get("policyName"),
                    "Connected": computer.get("connected"),
                    "Operating System": computer.get("osName"),
                    "Last Updated": computer.get("last_update"),
                    "Agent Version": computer.get("agentVersion	"),
                }

                # Attach as csv
                csv_output = flat_dict_to_csv(computer_info)
                siemplify.result.add_entity_table(entity.identifier, csv_output)

                json_result[entity.identifier] = computer
                enriched_entities.append(entity)

        except Exception as e:
            errors += f"Unable to get system info of {entity.identifier}: \n{e}\n"
            continue

    if enriched_entities:
        entities_names = [entity.identifier for entity in enriched_entities]
        output_message = (
            "Carbon Black Protection - Enriched the following entities\n"
            + "\n".join(entities_names)
        )
        output_message += errors

        siemplify.update_entities(enriched_entities)

    else:
        output_message = "Carbon Black Protection - No entities were enriched.\n"
        output_message += errors

    siemplify.result.add_result_json(convert_dict_to_json_result_dict(json_result))
    siemplify.end(output_message, "true")


if __name__ == "__main__":
    main()
