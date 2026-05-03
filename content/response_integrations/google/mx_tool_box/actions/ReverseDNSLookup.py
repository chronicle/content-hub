from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyAction import SiemplifyAction
from ..core.MXToolBoxManager import MXToolBoxManager
from soar_sdk.SiemplifyUtils import construct_csv, convert_dict_to_json_result_dict

MXTOOLBOX_PROVIDER = "MXToolBox"
SCRIPT_NAME = "MXToolBox_DNS_Lookup"
TABLE_NAME = "Results"


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
    result_domains = []
    result_dict = {}
    result_value = False
    json_results = {}

    target_entities = [
        entity
        for entity in siemplify.target_entities
        if entity.entity_type == EntityTypes.ADDRESS
    ]

    for entity in target_entities:
        try:
            result = mx_tool_box_manager.address_ptr_lookup(entity.identifier)
            if result:
                json_results[entity.identifier] = result
                success_entities.append(entity)
                result_value = True
                result_domains.extend([record.get("Domain Name") for record in result])
                domain_names = "; ".join(
                    [record.get("Domain Name") for record in result]
                )
                result_dict[entity.identifier] = domain_names
                # Enrich entity.
                entity.additional_properties.update(
                    {"MX_Reverse Lookup Domains": domain_names}
                )
                entity.is_enriched = True
                siemplify.result.add_entity_table(
                    entity.identifier, construct_csv(result)
                )

        except Exception as e:
            # An error occurred - skip entity and continue
            error_message = (
                f"An error occurred on entity: {entity.identifier}.\n{str(e)}."
            )
            siemplify.LOGGER.error(error_message)
            siemplify.LOGGER.exception(e)
            errors.append(error_message)

    if result_value:
        output_message = f"The following IPs were resolved: {', '.join([entity.identifier for entity in success_entities])}"

    else:
        output_message = "Not found data for target entities."

    if errors:
        output_message = "{0}  \n \n {1}".format(output_message, " \n ".join(errors))

    siemplify.update_entities(success_entities)
    # add json
    siemplify.result.add_result_json(convert_dict_to_json_result_dict(json_results))

    siemplify.end(output_message, ",".join(result_domains))


if __name__ == "__main__":
    main()
