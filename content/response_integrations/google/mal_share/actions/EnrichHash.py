from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler

# Imports
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import (
    dict_to_flat,
    flat_dict_to_csv,
    add_prefix_to_dict_keys,
    convert_dict_to_json_result_dict,
)
from ..core.MalShareManager import MalShareManager, MalShareError


# Enrich target entity with alienvault info and add csv table to entity
def enrich_entity(report, entity, siemplify):
    flat_report = dict_to_flat(report)
    csv_output = flat_dict_to_csv(flat_report)
    flat_report = add_prefix_to_dict_keys(flat_report, "MalShare")
    siemplify.result.add_entity_table(entity.identifier, csv_output)
    entity.additional_properties.update(flat_report)
    entity.is_enriched = True
    entity.is_suspicious = True


@output_handler
def main():
    siemplify = SiemplifyAction()
    entities_to_enrich = []
    not_found_entities = []
    json_results = {}
    output_message = ""
    result_value = True

    # Configuration.
    conf = siemplify.get_configuration("MalShare")
    api_key = conf["Api Key"]
    verify_ssl = conf.get("Verify SSL", "false").lower() == "true"
    malshare = MalShareManager(api_key, verify_ssl)

    for entity in siemplify.target_entities:
        if entity.entity_type == EntityTypes.FILEHASH:
            try:
                hash_info = malshare.search_hash(entity.identifier)
                if hash_info:
                    json_results[entity.identifier] = hash_info
                    enrich_entity(hash_info, entity, siemplify)
                    entities_to_enrich.append(entity)

            except MalShareError:
                # Hash is not found
                not_found_entities.append(entity)

            except Exception as e:
                # An error occurred - skip entity and continue
                siemplify.LOGGER.error(
                    f"An error occurred on entity: {entity.identifier}.\n{str(e)}."
                )
                siemplify.LOGGER.exception(e)

    if entities_to_enrich:
        output_message += (
            "The following entities were enriched by MalShare: \n{0}\n\n".format(
                "\n".join([entity.identifier for entity in entities_to_enrich])
            )
        )
        siemplify.update_entities(entities_to_enrich)

    if not_found_entities:
        output_message += "Can't find the following entities in MalShare: \n{0}".format(
            "\n".join([entity.identifier for entity in not_found_entities])
        )

    if not entities_to_enrich and not not_found_entities:
        output_message = "No entities were enriched."
        result_value = False

    # add json
    siemplify.result.add_result_json(convert_dict_to_json_result_dict(json_results))
    siemplify.end(output_message, result_value)


if __name__ == "__main__":
    main()
