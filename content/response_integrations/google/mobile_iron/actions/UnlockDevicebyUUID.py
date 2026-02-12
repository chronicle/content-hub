from __future__ import annotations

from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

# Imports
from ..core.MobileIronManager import MobileIronManager

# Consts.
PROVIDER_NAME = "MobileIron"
ACTION_NAME = "MobileIron_Unlock Device by UUID"
TABLE_HEADER = "Devices"


@output_handler
def main():
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
    device_uuid = siemplify.parameters.get("Device UUID")

    if device_uuid:
        mobile_iron_manager.unlock_device_by_uuid(device_uuid)
    else:
        raise Exception("Device UUID can not be empty.")

    output_message = f"System information fetched for UUID {device_uuid}"

    siemplify.end(output_message, True)


if __name__ == "__main__":
    main()
