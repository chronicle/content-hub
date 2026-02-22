from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler

# Imports
from ..core.MobileIronManager import MobileIronManager
from soar_sdk.SiemplifyAction import SiemplifyAction


# Consts.
PROVIDER_NAME = "MobileIron"
ACTION_NAME = "MobileIron_Ping"


@output_handler
def main():
    # Configuration.
    siemplify = SiemplifyAction()
    siemplify.script_name = ""
    configuretion_settings = siemplify.get_configuration(PROVIDER_NAME)
    api_root = configuretion_settings["API Root"]
    username = configuretion_settings["Username"]
    password = configuretion_settings["Password"]
    admin_device_id = configuretion_settings.get("Admin Device ID", 1)
    connected_cloud = (
        configuretion_settings.get("Cloud Instance", "false").lower() == "true"
    )
    verify_ssl = configuretion_settings.get("Verify SSL", "false").lower() == "true"

    mobile_iron_manager = MobileIronManager(
        api_root, username, password, admin_device_id, connected_cloud, verify_ssl
    )
    result_value = mobile_iron_manager.ping()

    if result_value:
        output_message = "Connection Established."
    else:
        output_message = "Failed to establish connection."

    siemplify.end(output_message, result_value)


if __name__ == "__main__":
    main()
