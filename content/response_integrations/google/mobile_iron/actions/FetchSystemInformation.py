from __future__ import annotations

from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyUtils import dict_to_flat, flat_dict_to_csv, output_handler

# Imports
from ..core.MobileIronManager import MobileIronManager

# Consts.
PROVIDER_NAME = "MobileIron"
ACTION_NAME = "MobileIron_Fetch System Information"
TABLE_HEADER = "Devices"


@output_handler
def main():
    # Variables Definition.
    result_value = False
    success_entities = []
    errors = []

    # Configuration.
    siemplify = SiemplifyAction()
    siemplify.script_name = ACTION_NAME
    configuretion_settings = siemplify.get_configuration(PROVIDER_NAME)
    api_root = configuretion_settings["API Root"]
    username = configuretion_settings["Username"]
    password = configuretion_settings["Password"]
    admin_device_id = configuretion_settings.get("Admin Device ID", 1)
    connected_cloud = configuretion_settings.get("Cloud Instance", "false").lower() == "true"
    verify_ssl = configuretion_settings.get("Verify SSL", "false").lower() == "true"

    mobile_iron_manager = MobileIronManager(
        api_root, username, password, admin_device_id, connected_cloud, verify_ssl
    )

    # Parameters.
    fields_to_fetch = siemplify.parameters.get("Fields To Fetch")

    target_entities = [
        entity for entity in siemplify.target_entities if entity.entity_type == EntityTypes.ADDRESS
    ]

    for entity in target_entities:
        try:
            system_information = mobile_iron_manager.fetch_device_information_by_ip(
                entity.identifier, fields_to_fetch=fields_to_fetch
            )
            if system_information:
                siemplify.result.add_entity_table(
                    entity.identifier,
                    flat_dict_to_csv(dict_to_flat(system_information)),
                )
                result_value = True
                success_entities.append(entity)
        except Exception as err:
            error_message = (
                f"Failed fetching system information for '{entity.identifier}', ERROR: {err}"
            )
            siemplify.LOGGER.error(error_message)
            siemplify.LOGGER.exception(err)
            errors.append(error_message)

    if success_entities:
        output_message = f"System information fetched for {','.join([entity.identifier for entity in success_entities])}"
    else:
        output_message = "No information was fetched for entities."

    if errors:
        output_message = "{0}\n\nErrors:\n{1}".format(output_message, "\n".join(errors))

    siemplify.end(output_message, result_value)


if __name__ == "__main__":
    main()
