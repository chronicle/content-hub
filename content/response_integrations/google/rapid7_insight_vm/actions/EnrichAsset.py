from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyUtils import add_prefix_to_dict, convert_dict_to_json_result_dict
from soar_sdk.SiemplifyAction import SiemplifyAction
from ..core.Rapid7Manager import Rapid7Manager
from TIPCommon import dict_to_flat, flat_dict_to_csv

SCRIPT_NAME = "Rapid7InsightVm - Enrich Asset"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = SCRIPT_NAME
    conf = siemplify.get_configuration("Rapid7InsightVm")
    rapid7_manager = Rapid7Manager(
        conf["Api Root"],
        conf["Username"],
        conf["Password"],
        conf.get("Verify SSL", "false").lower() == "true",
    )

    enriched_entities = []
    json_results = {}

    for entity in siemplify.target_entities:
        try:
            asset_details = None

            if entity.entity_type == EntityTypes.ADDRESS:
                asset_details = rapid7_manager.get_asset_by_ip(entity.identifier)

            elif entity.entity_type == EntityTypes.HOSTNAME:
                asset_details = rapid7_manager.get_asset_by_hostname(entity.identifier)

            if asset_details:
                json_results[entity.identifier] = asset_details

                constructed_asset_details = rapid7_manager.construct_asset_info(
                    asset_details
                )

                entity.additional_properties.update(
                    add_prefix_to_dict(constructed_asset_details, "Rapid7InsightVm")
                )
                entity.is_enriched = True

                siemplify.result.add_entity_table(
                    entity.identifier,
                    flat_dict_to_csv(dict_to_flat(constructed_asset_details)),
                )

                enriched_entities.append(entity)

        except Exception as e:
            # An error occurred - skip entity and continue
            siemplify.LOGGER.error(
                f"An error occurred on entity: {entity.identifier}.\n{str(e)}."
            )
            siemplify.LOGGER.exception(e)

    if enriched_entities:
        entities_names = [entity.identifier for entity in enriched_entities]

        output_message = (
            "The following entities were enriched by Rapid7 InsightVm:\n"
            + "\n".join(entities_names)
        )

        siemplify.update_entities(enriched_entities)

    else:
        output_message = "No hosts were enriched."

    # add json
    siemplify.result.add_result_json(convert_dict_to_json_result_dict(json_results))
    siemplify.end(output_message, "true")


if __name__ == "__main__":
    main()
