from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler

# ==============================================================================
# Remarks:

#  'get_hash_reputation' return 404 from API.

# ==============================================================================
from soar_sdk.SiemplifyAction import SiemplifyAction
from ..core.SentinelOneManager import SentinelOneManager
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyUtils import add_prefix_to_dict_keys, dict_to_flat, flat_dict_to_csv

# Consts.
SENTINEL_ONE_PROVIDER = "SentinelOne"
SENTINEL_PREFIX = "SENO_"
FILEHASH = EntityTypes.FILEHASH


@output_handler
def main():
    # Define Variables.
    entities_successed = []
    result_value = False
    # Configuration.
    siemplify = SiemplifyAction()
    conf = siemplify.get_configuration(SENTINEL_ONE_PROVIDER)
    sentinel_one_manager = SentinelOneManager(
        conf["Api Root"], conf["Username"], conf["Password"]
    )

    # Get scope entities.
    scope_entities = [
        entity for entity in siemplify.target_entities if entity.entity_type == FILEHASH
    ]

    # Run on entities.
    for entity in scope_entities:
        hash_reputation = sentinel_one_manager.get_hash_reputation(entity.identifier)
        if hash_reputation:
            entities_successed.append(entity)
            result_value = True
            # Organize output.
            hash_reputation_flat = dict_to_flat(hash_reputation)
            csv_output = flat_dict_to_csv(hash_reputation_flat)
            # Add entity table.
            siemplify.result.add_entity_table(entity.identifier, csv_output)
            # Enrich entity.
            entity.additional_data.update(
                add_prefix_to_dict_keys(hash_reputation_flat, SENTINEL_PREFIX)
            )

    if entities_successed:
        output_message = "Found hash reputation for: {0}".format(f",")
    else:
        output_message = "No hash reputation found for target entities."

    siemplify.update_entities(entities_successed)
    siemplify.end(output_message, result_value)


if __name__ == "__main__":
    main()
