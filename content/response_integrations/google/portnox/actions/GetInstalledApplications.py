from __future__ import annotations

from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyUtils import construct_csv, output_handler

from ..core.PortnoxManager import PortnoxManager

SCRIPT_NAME = "Portnox - GetInstalledApplications"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = SCRIPT_NAME
    conf = siemplify.get_configuration("Portnox")
    api_root = conf["Api Root"]
    username = conf["Username"]
    password = conf["Password"]
    use_ssl = str(conf.get("Verify SSL", "False")).lower() == "true"
    portnox_manager = PortnoxManager(api_root, username, password, use_ssl)
    enriched_entities = []

    for entity in siemplify.target_entities:
        try:
            device = None

            if entity.entity_type == EntityTypes.ADDRESS:
                device = portnox_manager.search_device("ip", entity.identifier)

            elif entity.entity_type == EntityTypes.MACADDRESS:
                device = portnox_manager.search_device("macAddress", entity.identifier)

            if device:
                device_id = device["id"]
                installed_applications = portnox_manager.get_device_installed_applications(
                    device_id
                )

                if installed_applications:
                    csv_output = construct_csv(installed_applications)

                    siemplify.result.add_entity_table(
                        f"{entity.identifier} - Installed Applications", csv_output
                    )

                    enriched_entities.append(entity)

        except Exception as e:
            # An error occurred - skip entity and continue
            siemplify.LOGGER.error(f"An error occurred on entity: {entity.identifier}.\n{str(e)}.")

    if enriched_entities:
        entities_names = [entity.identifier for entity in enriched_entities]

        output_message = (
            "Installed applications were found for the following entities:\n"
            + "\n".join(entities_names)
        )

        siemplify.update_entities(enriched_entities)

    else:
        output_message = "No isntalled applications were found."

    siemplify.end(output_message, "true")


if __name__ == "__main__":
    main()
