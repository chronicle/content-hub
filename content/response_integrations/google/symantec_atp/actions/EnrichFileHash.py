from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyAction import SiemplifyAction
from ..core.SymantecATPManager import SymantecATPManager
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyUtils import dict_to_flat, flat_dict_to_csv

ATP_PROVIDER = "SymantecATP"
RESULT_TABLE_NAME = "Command IDs"
ACTION_NAME = "SymantecATP_Get File Details"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = ACTION_NAME
    conf = siemplify.get_configuration(ATP_PROVIDER)
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")
    verify_ssl = conf.get("Verify SSL", "false").lower() == "true"
    atp_manager = SymantecATPManager(
        conf.get("API Root"),
        conf.get("Client ID"),
        conf.get("Client Secret"),
        verify_ssl,
    )

    result_value = False
    errors = []
    success_entities = []
    max_file_health = 0

    target_entities = [
        entity
        for entity in siemplify.target_entities
        if entity.entity_type == EntityTypes.FILEHASH
    ]

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    for entity in target_entities:
        siemplify.LOGGER.info(f"Started processing entity: {entity.identifier}")
        try:
            file_details = atp_manager.get_file_details_by_hash(entity.identifier)

            if file_details:

                if int(file_details.get("file_health", 0)) > max_file_health:
                    max_file_health = file_details.get("file_health", 0)

                file_details_flat = dict_to_flat(file_details)
                csv_result = flat_dict_to_csv(file_details_flat)
                # Add Table.
                siemplify.result.add_entity_table(entity.identifier, csv_result)
                # Enrich Entity.
                entity.additional_properties.update(file_details_flat)
                success_entities.append(entity)
                result_value = True

                siemplify.LOGGER.info(f"Finished processing entity {entity.identifier}")

        except Exception as err:
            error_message = f'Error fetching file details for  "{entity.identifier}", Error: {str(err)}'
            siemplify.LOGGER.error(error_message)
            siemplify.LOGGER.exception(err)
            errors.append(error_message)

    if result_value:
        output_message = f'{",".join([entity.identifier for entity in success_entities])} were enriched.'
    else:
        output_message = "No entities were enriched."

    # Attach errors if exists.
    if errors:
        output_message = "{0},\n\nERRORS:\n{1}".format(
            output_message, " \n ".join(errors)
        )

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  max_file_health: {max_file_health}\n output_message: {output_message}"
    )

    siemplify.end(output_message, max_file_health)


if __name__ == "__main__":
    main()
