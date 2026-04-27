from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyDataModel import EntityTypes

# Imports
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import (
    dict_to_flat,
    flat_dict_to_csv,
    convert_dict_to_json_result_dict,
)
from ..core.CynetManager import CynetManager
from TIPCommon import extract_configuration_param

# Consts
FILEHASH = EntityTypes.FILEHASH
INTEGRATION_NAME = "Cynet"


# add entity table with hash details from Cynet
def entity_report(report, entity, siemplify):
    flat_report = dict_to_flat(report)
    siemplify.result.add_entity_table(entity.identifier, flat_dict_to_csv(flat_report))
    return True


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = "Cynet - HashQuery"
    results_json = {}
    query_entities = []
    hash_report = {}

    # Configuration.
    conf = siemplify.get_configuration("Cynet")
    api_root = conf["Api Root"]
    username = conf["Username"]
    password = conf["Password"]
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        default_value=False,
        input_type=bool,
    )
    cynet_manager = CynetManager(api_root, username, password, verify_ssl)

    for entity in siemplify.target_entities:
        try:
            if entity.entity_type == FILEHASH:
                hash_lower = entity.identifier.lower()
                # Define if file hash type is sha256 or not
                is_sha256 = cynet_manager.is_sha256(hash_lower)

                if is_sha256:
                    hash_report = cynet_manager.get_hash_details(hash_lower)

                if hash_report:
                    results_json[entity.identifier] = hash_report
                    entity_report(hash_report, entity, siemplify)
                    query_entities.append(entity)

        except Exception as e:
            # An error occurred - skip entity and continue
            siemplify.LOGGER.error(
                f"An error occurred on entity: {entity.identifier}.\n{str(e)}."
            )
            siemplify.LOGGER.exception(e)

    if query_entities:
        output_message = f"Following entities were queried by Cynet. \n{query_entities}"
        result_value = "true"
    else:
        output_message = "No entities were queried."
        result_value = "false"

    siemplify.result.add_result_json(convert_dict_to_json_result_dict(results_json))
    siemplify.end(output_message, result_value)


if __name__ == "__main__":
    main()
