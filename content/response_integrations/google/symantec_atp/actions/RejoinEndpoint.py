from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyAction import SiemplifyAction
from ..core.SymantecATPManager import SymantecATPManager
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyUtils import construct_csv

ATP_PROVIDER = "SymantecATP"
RESULT_TABLE_NAME = "Command IDs"
ACTION_NAME = "SymantecATP_Rejoin Endpoint"
INSIGHT_MESSAGE = "Rejoin command sent."


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = ACTION_NAME
    conf = siemplify.get_configuration(ATP_PROVIDER)
    verify_ssl = conf.get("Verify SSL", "false").lower() == "true"
    atp_manager = SymantecATPManager(
        conf.get("API Root"),
        conf.get("Client ID"),
        conf.get("Client Secret"),
        verify_ssl,
    )

    errors = []
    command_ids_csv = []
    rejoined_entities = []
    command_ids = []

    target_entities = [
        entity
        for entity in siemplify.target_entities
        if entity.entity_type == EntityTypes.ADDRESS
        or entity.entity_type == EntityTypes.HOSTNAME
    ]

    for entity in target_entities:
        try:
            command_id = None
            if entity.entity_type == EntityTypes.ADDRESS:
                entity_uuid = atp_manager.get_endpoint_uuid_by_ip(entity.identifier)
            else:
                entity_uuid = atp_manager.get_endpoint_uuid_by_hostname(
                    entity.identifier
                )

            if entity_uuid:
                command_id = atp_manager.rejoin_endpoint_by_uid(entity_uuid)

            if command_id:
                command_ids_csv.append(
                    {"Entity Identifier": entity.identifier, "Command ID": command_id}
                )
                siemplify.add_entity_insight(
                    entity, INSIGHT_MESSAGE, triggered_by=ATP_PROVIDER
                )
                rejoined_entities.append(entity)
                command_ids.append(command_id)

        except Exception as err:
            error_message = f'Error rejoin "{entity.identifier}", Error: {str(err)}'
            siemplify.LOGGER.error(error_message)
            siemplify.LOGGER.exception(err)
            errors.append(error_message)

    # Check if CSV contain values and not only header.
    if command_ids_csv:
        output_message = f"{','.join([entity.identifier for entity in rejoined_entities])} rejoined successfully."

        siemplify.result.add_data_table(
            RESULT_TABLE_NAME, construct_csv(command_ids_csv)
        )

    else:
        output_message = "No entities were rejoined."

    # Attach errors if exists.
    if errors:
        output_message = "{0},\n\nERRORS:\n{1}".format(
            output_message, " \n ".join(errors)
        )

    siemplify.end(output_message, ",".join(command_ids))


if __name__ == "__main__":
    main()
