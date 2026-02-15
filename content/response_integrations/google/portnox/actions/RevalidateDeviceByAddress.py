from __future__ import annotations

from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyUtils import output_handler

from ..core.PortnoxManager import PortnoxManager

SCRIPT_NAME = "Portnox - RevalidateDeviceByIpOrMac"


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

    entities = []
    device_ids = []

    for entity in siemplify.target_entities:
        try:
            device = None

            if entity.entity_type == EntityTypes.ADDRESS:
                device = portnox_manager.search_device("ip", entity.identifier)

            elif entity.entity_type == EntityTypes.MACADDRESS:
                device = portnox_manager.search_device("macAddress", entity.identifier)

            if device:
                device_id = device["id"]
                portnox_manager.revalidate_device(device_id)
                device_ids.append((entity, device_id))

        except Exception as e:
            # An error occurred - skip entity and continue
            siemplify.LOGGER.error(
                f"Unable to revalidate device for entity: {entity.identifier}.\n{str(e)}."
            )

    for entity, device_id in device_ids:
        try:
            portnox_manager.wait_for_device_revalidation(device_id)
            entities.append(entity)

        except Exception as e:
            # An error occurred - skip entity and continue
            siemplify.LOGGER.error(
                f"Unable to verify revalidation device for entity: {entity.identifier}.\n{str(e)}."
            )
            siemplify.LOGGER.exception(e)

    if entities:
        entities_names = [entity.identifier for entity in entities]

        output_message = "Devices were revalidated for the following entities:\n" + "\n".join(
            entities_names
        )

    else:
        output_message = "No devices were revalidated."

    siemplify.end(output_message, "true")


if __name__ == "__main__":
    main()
