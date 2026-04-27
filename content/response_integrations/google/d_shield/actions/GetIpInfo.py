from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyDataModel import EntityTypes

# Imports
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import (
    dict_to_flat,
    flat_dict_to_csv,
    add_prefix_to_dict_keys,
    convert_dict_to_json_result_dict,
)
from ..core.DShieldManager import DShieldManager

# Consts
ADDRESS = EntityTypes.ADDRESS


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = "DShield - Get IP Info"

    # Configuration.
    conf = siemplify.get_configuration("DShield")
    api_root = conf["Api Root"]
    dshield = DShieldManager(api_root)

    ip_to_enrich = []
    json_results = {}

    for entity in siemplify.target_entities:
        if entity.entity_type == ADDRESS and not entity.is_internal:
            try:
                ip_info = dshield.get_ip_info(entity.identifier)

                if ip_info:
                    json_results[entity.identifier] = ip_info
                    flat_report = dict_to_flat(ip_info)
                    # Enrich and add csv table
                    csv_output = flat_dict_to_csv(flat_report)
                    flat_report = add_prefix_to_dict_keys(flat_report, "DShield")
                    siemplify.result.add_entity_table(entity.identifier, csv_output)
                    entity.additional_properties.update(flat_report)

                    ip_to_enrich.append(entity)
                    entity.is_enriched = True

            except Exception as e:
                # An error occurred - skip entity and continue
                siemplify.LOGGER.error(
                    f"An error occurred on entity: {entity.identifier}.\n{str(e)}."
                )
                siemplify.LOGGER.exception(e)

    if ip_to_enrich:
        output_message = (
            f"Following addresses were enriched by DShield. \n{ip_to_enrich}"
        )
        result_value = "true"
        siemplify.update_entities(ip_to_enrich)
    else:
        output_message = "No entities were enriched."
        result_value = "false"
    # add json
    siemplify.result.add_result_json(convert_dict_to_json_result_dict(json_results))
    siemplify.end(output_message, result_value)


if __name__ == "__main__":
    main()
