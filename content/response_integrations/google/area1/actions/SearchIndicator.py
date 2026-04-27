from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import (
    dict_to_flat,
    flat_dict_to_csv,
    add_prefix_to_dict,
    convert_dict_to_json_result_dict,
)
from ..core.Area1Manager import Area1Manager

ACTION_NAME = "Area1_Search Indicators"
AREA1_PREFIX = "area1_"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = ACTION_NAME
    configurations = siemplify.get_configuration("Area1")
    server_addr = configurations["Api Root"]
    username = configurations["Username"]
    password = configurations["Password"]
    verify_ssl = configurations.get("Verify SSL", "false").lower() == "true"

    area1_manager = Area1Manager(server_addr, username, password, verify_ssl)

    json_result = {}
    enriched_entities = []

    for entity in siemplify.target_entities:
        try:
            indicator_data = area1_manager.search_indicator(entity.identifier)

            if indicator_data:
                json_result[entity.identifier] = indicator_data
                flat_indicator_data = dict_to_flat(indicator_data)
                siemplify.result.add_entity_table(
                    entity.identifier, flat_dict_to_csv(flat_indicator_data)
                )

                entity.additional_properties.update(
                    add_prefix_to_dict(flat_indicator_data, AREA1_PREFIX)
                )
                entity.is_enriched = True

                enriched_entities.append(entity)

        except Exception as err:
            error_message = f"Failed fetching indicator data for {entity.identifier}"
            siemplify.LOGGER.error(error_message)
            siemplify.LOGGER.exception(err)

    if enriched_entities:
        entities_names = [entity.identifier for entity in enriched_entities]

        output_message = "Found indicators for the following entities:\n" + "\n".join(
            entities_names
        )

        siemplify.update_entities(enriched_entities)

    else:
        output_message = "No indicators found for target entities."

    siemplify.result.add_result_json(convert_dict_to_json_result_dict(json_result))
    siemplify.end(output_message, "true")


if __name__ == "__main__":
    main()
