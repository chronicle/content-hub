from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyAction import SiemplifyAction
from ..core.MXToolBoxManager import MXToolBoxManager
from soar_sdk.SiemplifyUtils import (
    get_domain_from_entity,
    construct_csv,
    convert_dict_to_json_result_dict,
)

MXTOOLBOX_PROVIDER = "MXToolBox"
SCRIPT_NAME = "MXToolBox_A_Lookup"
TABLE_HEADER = "A Record Lookup Results"


@output_handler
def main():
    # Configurations.
    siemplify = SiemplifyAction()
    siemplify.script_name = SCRIPT_NAME
    conf = siemplify.get_configuration(MXTOOLBOX_PROVIDER)
    verify_ssl = conf["Verify SSL"].lower() == "true"
    mx_tool_box_manager = MXToolBoxManager(
        conf["API Root"], conf["API Key"], verify_ssl
    )

    # Variables.
    errors = []
    success_entities = []
    ip_addresses = []
    entities_results = []
    result_value = False
    json_results = {}

    target_entities = [
        entity
        for entity in siemplify.target_entities
        if entity.entity_type == EntityTypes.HOSTNAME
        or entity.entity_type == EntityTypes.URL
        or entity.entity_type == EntityTypes.USER
    ]

    for entity in target_entities:
        try:
            result = mx_tool_box_manager.domain_a_lookup(get_domain_from_entity(entity))
            if result:
                json_results[entity.identifier] = result
                success_entities.append(entity)
                ip_addresses_string = ",".join(
                    [record.get("IP Address") for record in result]
                )
                entities_results.append(
                    {
                        "Domain/IP": entity.identifier,
                        "Resolved IP Address": ip_addresses_string,
                    }
                )
                entity.additional_properties.update(
                    {"MX_IP Addresses": ip_addresses_string}
                )
                entity.is_enriched = True

                for record in result:
                    ip_addresses.append(record.get("IP Address"))

                result_value = True

        except Exception as e:
            # An error occurred - skip entity and continue
            error_message = (
                f"An error occurred on entity: {entity.identifier}.\n {str(e)}."
            )
            siemplify.LOGGER.error(error_message)
            siemplify.LOGGER.exception(e)
            errors.append(error_message)

    if result_value:
        output_message = f"The following domains were resolved: {', '.join([entity.identifier for entity in success_entities])}"
        siemplify.result.add_data_table(TABLE_HEADER, construct_csv(entities_results))
    else:
        output_message = "Not found data for target entities."

    if errors:
        output_message = "{0}  \n \n {1}".format(output_message, " \n ".join(errors))

    siemplify.update_entities(success_entities)
    # add json
    siemplify.result.add_result_json(convert_dict_to_json_result_dict(json_results))

    siemplify.end(output_message, ",".join(ip_addresses))


if __name__ == "__main__":
    main()
