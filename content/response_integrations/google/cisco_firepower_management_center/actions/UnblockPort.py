from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyAction import SiemplifyAction
from ..core.CiscoFirepowerManager import CiscoFirepowerManager

INTEGRATION_PROVIDER = "CiscoFirepowerManagementCenter"


@output_handler
def main():

    siemplify = SiemplifyAction()
    conf = siemplify.get_configuration(INTEGRATION_PROVIDER)
    verify_ssl = str(conf.get("Verify SSL", "false").lower()) == str(True).lower()

    cisco_firepower_manager = CiscoFirepowerManager(
        conf["API Root"], conf["Username"], conf["Password"], verify_ssl
    )
    # Parameters.
    url_group_name = siemplify.parameters.get("Port Group Name")
    port = siemplify.parameters.get("Port")

    # Set script name.
    siemplify.script_name = "CiscoFirepower_Unblock_Port"

    # Get url group object to pass to the block function.
    port_group_object = cisco_firepower_manager.get_port_group_object_by_name(
        url_group_name
    )

    result_value = cisco_firepower_manager.unblock_port(port_group_object, port)

    if result_value:
        output_message = f"Port {port} was unblocked."
    else:
        output_message = "No ports were unblocked."

    siemplify.end(output_message, result_value)


if __name__ == "__main__":
    main()
