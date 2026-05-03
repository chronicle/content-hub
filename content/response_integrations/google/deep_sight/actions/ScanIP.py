from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyDataModel import EntityTypes
from ..core.DeepSightManager import DeepSightManager
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import (
    dict_to_flat,
    add_prefix_to_dict_keys,
    flat_dict_to_csv,
    convert_dict_to_json_result_dict,
)

SCRIPT_NAME = "DeepSight - ScanIp"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = SCRIPT_NAME
    conf = siemplify.get_configuration("DeepSight")
    api_key = conf["ApiKey"]
    use_ssl = conf["Use SSL"].lower() == "true"

    deepsight_manager = DeepSightManager(api_key, use_ssl=use_ssl)
    enriched_entities = []
    json_results = {}

    for entity in siemplify.target_entities:
        try:
            if entity.entity_type == EntityTypes.ADDRESS:
                result = deepsight_manager.scan_ip(entity.identifier)

                if result:
                    json_results[entity.identifier] = result
                    flat_result = dict_to_flat(result)
                    flat_result = add_prefix_to_dict_keys(
                        flat_result,
                        "DeepSight"
                    )
                    csv_output = flat_dict_to_csv(flat_result)
                    siemplify.result.add_entity_table(
                        entity.identifier,
                        csv_output
                    )
                    entity.additional_properties.update(flat_result)
                    entity.is_enriched = True

                    enriched_entities.append(entity)

        except Exception as e:
            # An error occurred - skip entity and continue
            siemplify.LOGGER.error(
                f"An error occurred on entity: {entity.identifier}.\n{str(e)}."
            )
            siemplify.LOGGER._log.exception(e)

    if enriched_entities:
        entities_names = [entity.identifier for entity in enriched_entities]

        output_message = (
            "DeepSight: The following entities were enriched:\n"
            + "\n".join(entities_names)
        )
        siemplify.update_entities(enriched_entities)

    else:
        output_message = "DeepSight: No entities were enriched."

    # add json
    siemplify.result.add_result_json(
        convert_dict_to_json_result_dict(json_results)
    )
    siemplify.end(output_message, "true")


if __name__ == "__main__":
    main()
