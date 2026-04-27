from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyAction import SiemplifyAction
from ..core.SymantecATPManager import SymantecATPManager
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyUtils import dict_to_flat
from TIPCommon import construct_csv
import arrow

ATP_PROVIDER = "SymantecATP"
RESULT_TABLE_NAME = "Command IDs"
ACTION_NAME = "SymantecATP_Get Events For Entity."
SUPPORTED_ENTITY_TYPES = [EntityTypes.USER, EntityTypes.HOSTNAME, EntityTypes.ADDRESS]


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
    events_amount = 0
    search_field = ""

    # Parameters.
    minutes_back = int(siemplify.parameters.get("Minutes Back To Fetch"))

    target_entities = [
        entity
        for entity in siemplify.target_entities
        if entity.entity_type in SUPPORTED_ENTITY_TYPES
    ]

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    for entity in target_entities:
        try:
            siemplify.LOGGER.info(f"Started processing entity: {entity.identifier}")
            # Create arrow time object.
            time_object = arrow.now().shift(minutes=-minutes_back)

            if entity.entity_type == EntityTypes.ADDRESS:
                search_field = "device_ip"

            if entity.entity_type == EntityTypes.HOSTNAME:
                search_field = "device_name"

            if entity.entity_type == EntityTypes.USER:
                search_field = "user_name"

            result_events = atp_manager.get_event_for_entity_since(
                search_field, entity.identifier, time_object
            )
            if result_events:
                events_amount += len(result_events)
                query_result = list(map(dict_to_flat, result_events))
                csv_result = construct_csv(query_result)
                siemplify.result.add_entity_table(entity.identifier, csv_result)

                success_entities.append(entity)
                result_value = True
                siemplify.LOGGER.info(f"Finished processing entity {entity.identifier}")

        except Exception as err:
            error_message = (
                f'Error fetching events "{entity.identifier}", Error: {str(err)}'
            )
            siemplify.LOGGER.error(error_message)
            siemplify.LOGGER.exception(err)
            errors.append(error_message)

    if result_value:
        output_message = f'Found events for {",".join([entity.identifier for entity in success_entities])}.'
    else:
        output_message = "No events found for target entities."

    # Attach errors if exists.
    if errors:
        output_message = "{0},\n\nERRORS:\n{1}".format(
            output_message, " \n ".join(errors)
        )

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  events_amount: {events_amount}\n output_message: {output_message}"
    )

    siemplify.update_entities(success_entities)
    siemplify.end(output_message, events_amount)


if __name__ == "__main__":
    main()
