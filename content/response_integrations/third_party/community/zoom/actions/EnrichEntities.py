from __future__ import annotations

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyUtils import (
    add_prefix_to_dict,
    convert_dict_to_json_result_dict,
    dict_to_flat,
    output_handler,
)

from ..core.parameters import Parameters
from ..core.ZoomManager import ZoomManager

INTEGRATION_NAME = "Zoom"
SCRIPT_NAME = "Enrich Entities"

# This action does not need to change any data at the third party, but instead enriching the entity data in siemplify
# Adding additional_properties to the entity in siemplify.


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = SCRIPT_NAME

    # Extracting the integration params
    siemplify.LOGGER.info("------------------ Main Started -------------------")

    conf = siemplify.get_configuration(INTEGRATION_NAME)
    parameters = Parameters.from_conf(conf)

    # declaring an empty array  for the new data
    enriched_entities = []

    try:
        zoom_manager = ZoomManager(**parameters.as_dict(), logger=siemplify.LOGGER)

        # declaring an empty dictionary of the json_result
        json_result = {}

        # Iterate over all the entities data and does:
        # checks the entity type.
        # Searching for the relevant data for the specific user

        for entity in siemplify.target_entities:
            try:
                # checks the entity type.
                if entity.entity_type != EntityTypes.USER:
                    continue

                # Searching for the relevant data for the specific user
                user_info = zoom_manager.get_user_details(entity.identifier)

                # if the dictionary that contains the data has an hierarchy we need getting it flat, so we use this data
                flat_user_data = dict_to_flat(user_info)

                # adding the zoom prefix to each entity detail to enable the analysis of the entity data
                flat_user_data = add_prefix_to_dict(flat_user_data, "Zoom")

                # updating the additional_properties of the specific entity.
                entity.additional_properties.update(flat_user_data)

                # adding the relevant identifier and assign the user_info into the array,
                # using this function we need to use
                # `siemplify.result.add_result_json(convert_dict_to_json_result_dict(json_result))`
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
            # BUG: during refactoring found this string returned instead of boolean value.
            # Possibly people are already using this functional,
            # so Couldn't change it without breaking the backward capability
            return_value = "True"
            siemplify.update_entities(enriched_entities)
            status = EXECUTION_STATE_COMPLETED

        else:
            output_message = "No entities were enriched."
            return_value = "False"
            status = EXECUTION_STATE_FAILED

        siemplify.result.add_result_json(convert_dict_to_json_result_dict(json_result))

    except Exception as e:
        output_message = f"No entities were enriched. Error: {e}"
        return_value = "False"
        status = EXECUTION_STATE_FAILED

    finally:
        siemplify.end(output_message, return_value, status)
        if status is EXECUTION_STATE_FAILED:
            siemplify.LOGGER.error("Error trying to connect to ZOOM")
            siemplify.LOGGER.exception(output_message)
            raise


if __name__ == "__main__":
    main()
