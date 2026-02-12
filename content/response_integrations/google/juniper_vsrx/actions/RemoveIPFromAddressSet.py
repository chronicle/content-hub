from __future__ import annotations

from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyUtils import output_handler

from ..core.JuniperVSRXManager import JuniperVSRXManager

PROVIDER_NAME = "JuniperVSRX"
ACTION_NAME = "JuniperVSRX Remove IP From Address Set"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = ACTION_NAME
    config = siemplify.get_configuration(PROVIDER_NAME)
    address = config["Address"]
    port = config["Port"]
    username = config["Username"]
    password = config["Password"]

    juniper_manager = JuniperVSRXManager(address, port, username, password)
    result_value = False
    errors = []
    success_entities = []

    # Parameters.
    address_set_name = siemplify.parameters.get("Address Set Name")
    zone_name = siemplify.parameters.get("Zone Name")

    address_entities = [
        entity for entity in siemplify.target_entities if entity.entity_type == EntityTypes.ADDRESS
    ]

    for entity in address_entities:
        try:
            juniper_manager.remove_ip_from_address_set(
                entity.identifier, address_set_name, zone_name
            )
            success_entities.append(entity)
        except Exception as err:
            error_message = f'Error removing address "{entity.identifier}" from address-set "{address_set_name}", ERROR: {err}'
            siemplify.LOGGER.error(error_message)
            siemplify.LOGGER.exception(err)
            errors.append(error_message)

    juniper_manager.commit_config_changes()
    juniper_manager.close_session()

    if success_entities:
        output_message = f'{", ".join([entity.identifier for entity in success_entities])} were removed from address-set "{address_set_name}"'
        result_value = True
    else:
        output_message = f'No entities were removed from address-set "{address_set_name}"'

    if errors:
        output_message = "{0}, \n \n Errors: {1}".format(output_message, "\n ".join(errors))

    siemplify.end(output_message, result_value)


if __name__ == "__main__":
    main()
