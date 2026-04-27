from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import (
    dict_to_flat,
    add_prefix_to_dict_keys,
    flat_dict_to_csv,
    convert_dict_to_json_result_dict,
)
from ..core.SEPManager import SEP14Manager
from TIPCommon import extract_configuration_param


INTEGRATION_NAME = "SEP"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = "SEP - Get System Info"
    output_message = ""
    result_value = "false"
    errors = ""

    conf = siemplify.get_configuration("SEP")
    username = conf["Username"]
    password = conf["Password"]
    domain = conf["Domain"]
    url = conf["Api Root"]
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        input_type=bool,
        default_value=False,
    )
    sep_manager = SEP14Manager(url, username, password, domain, verify_ssl=verify_ssl)

    enriched_entities = []
    json_result = {}

    for entity in siemplify.target_entities:
        if entity.entity_type == EntityTypes.HOSTNAME:
            try:
                system_info = sep_manager.getComputerInfo(entity.identifier)

                if system_info:
                    json_result[entity.identifier] = system_info
                    flat_report = dict_to_flat(system_info)

                    # Enrich and add csv table
                    csv_output = flat_dict_to_csv(flat_report)
                    flat_report = add_prefix_to_dict_keys(flat_report, "SEP")
                    siemplify.result.add_entity_table(entity.identifier, csv_output)
                    entity.additional_properties.update(flat_report)

                    enriched_entities.append(entity)
                    entity.is_enriched = True
                    result_value = "true"

            except Exception as e:
                errors += f"Unable to get info for {entity.identifier}: \n{e}\n"
                siemplify.LOGGER.error(
                    f"An error occurred on entity: {entity.identifier}.\n{str(e)}."
                )
                siemplify.LOGGER.exception(e)
                continue

    if enriched_entities:
        entities_names = [entity.identifier for entity in enriched_entities]

        output_message += "Following entities were enriched by SEP\n" + "\n".join(
            entities_names
        )
        output_message += errors

        siemplify.update_entities(enriched_entities)

    else:
        output_message += "No entities were enriched.\n"
        output_message += errors

    siemplify.result.add_result_json(convert_dict_to_json_result_dict(json_result))
    siemplify.end(output_message, result_value)


if __name__ == "__main__":
    main()
