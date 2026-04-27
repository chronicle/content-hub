from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyDataModel import EntityTypes
from ..core.CylanceManager import CylanceManager

SCRIPT_NAME = "Cylance - ChangeZone"


@output_handler
def main():
    siemplify = SiemplifyAction()
    conf = siemplify.get_configuration("Cylance")
    siemplify.script_name = SCRIPT_NAME

    server_address = conf["Server Address"]
    application_secret = conf["Application Secret"]
    application_id = conf["Application ID"]
    tenant_identifier = conf["Tenant Identifier"]

    cm = CylanceManager(
        server_address, application_id, application_secret, tenant_identifier
    )

    zones_to_add = siemplify.parameters.get("Zones to Add")
    zones_to_remove = siemplify.parameters.get("Zones to Remove")

    affected_entities = []

    if zones_to_add or zones_to_remove:
        zones_to_add = zones_to_add.split(",") if zones_to_add else []
        zones_to_remove = zones_to_remove.split(",") if zones_to_remove else []

        for entity in siemplify.target_entities:
            try:
                if entity.entity_type == EntityTypes.ADDRESS:
                    device_id = cm.get_device_by_name(
                        entity.identifier, is_address=True
                    )
                    cm.change_device_zone(
                        device_id,
                        zone_names_to_add=zones_to_add,
                        zone_names_to_remove=zones_to_remove,
                    )

                    affected_entities.append(entity)

                elif entity.entity_type == EntityTypes.HOSTNAME:
                    device_id = cm.get_device_by_name(entity.identifier)
                    cm.change_device_zone(
                        device_id,
                        zone_names_to_add=zones_to_add,
                        zone_names_to_remove=zones_to_remove,
                    )
                    affected_entities.append(entity)

            except Exception as e:
                # An error occurred - skip entity and continue
                siemplify.LOGGER.error(
                    f"An error occurred on entity: {entity.identifier}.\n{str(e)}."
                )
                siemplify.LOGGER._log.exception(e)

    if affected_entities:
        entities_names = [entity.identifier for entity in affected_entities]

        output_message = "Following entities were affected:\n" + "\n".join(
            entities_names
        )
        if zones_to_add:
            output_message += (
                "\n\n" + "Added to the following zones:\n" + "\n".join(zones_to_add)
            )
        if zones_to_remove:
            output_message += (
                "\n\n"
                + "Removed from the following zones:\n"
                + "\n".join(zones_to_remove)
            )

    else:
        output_message = "No entities were affected."

    siemplify.end(output_message, "true")


if __name__ == "__main__":
    main()
