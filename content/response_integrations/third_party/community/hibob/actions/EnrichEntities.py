from __future__ import annotations

from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyUtils import (
    add_prefix_to_dict,
    convert_dict_to_json_result_dict,
    output_handler,
)

from ..core.HibobManager import HibobManager, dict_to_flat

INTEGRATION_NAME = "Hibob"

# This action does not need to change any data at the third party, but instead enriching the entity data in siemplify
# Adding additional_properties to the entity in siemplify.


@output_handler
def main():
    siemplify = SiemplifyAction()

    conf = siemplify.get_configuration(INTEGRATION_NAME)

    # The api_root is the url of the integration :https://api.hibob.com/
    api_root = "https://api.hibob.com"

    # The api_token generated from hibob site
    api_token = conf.get("API Token")

    boolean_get_user_image = siemplify.extract_action_param("Get User Image")

    # creating an instance of hibobmanager object
    hibob_manager = HibobManager(api_root, api_token)

    # declaring an empty array  for the new data
    enriched_entities = []

    # declaring an empty dictionary of the json_result
    json_result = {}

    # Itirate over all the entities data and does:
    # checks the entity type.
    # Searching for the relevant data for the specific user

    for entity in siemplify.target_entities:
        try:
            # checks the entity type.
            if entity.entity_type == EntityTypes.USER:
                # Searching for the relevant data for the specific user
                search_results = hibob_manager.get_user_details(entity.identifier)

                if search_results:
                    user_info = search_results
                    # if the dictionary that contains the data has an hierarchy we need getting it flat so we use this data
                    flat_user_data = dict_to_flat(user_info)

                    # adding the hibob prefix to each entity detail to enable the analysis of the entity data
                    flat_user_data = add_prefix_to_dict(flat_user_data, "Hibob")
                    # updating the additional_properties of the specific entity.
                    entity.additional_properties.update(flat_user_data)

                    # adding the relevant identifier and assign the user_info into the array,
                    # if using this function we need to use siemplify.result.add_result_json(convert_dict_to_json_result_dict(json_result))
                    json_result[entity.identifier] = user_info
                    # adding the enriched_entities to the dictionary
                    enriched_entities.append(entity)

                    entity.is_enriched = True

        except Exception as e:
            # An error occurred - skip entity and continue
            siemplify.LOGGER.error(
                f"An error occurred on entity: {entity.identifier}.\n{e!s}.",
            )
            siemplify.LOGGER.exception(e)

    if enriched_entities:
        entities_names = [entity.identifier for entity in enriched_entities]

        output_message = "The following entities were enriched:\n" + "\n".join(
            entities_names,
        )
        return_value = "True"

        siemplify.update_entities(enriched_entities)

    else:
        output_message = "No entities were enriched."
        return_value = "False"

    siemplify.result.add_result_json(convert_dict_to_json_result_dict(json_result))

    siemplify.end(output_message, return_value)


if __name__ == "__main__":
    main()
