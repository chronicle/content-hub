from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyAction import SiemplifyAction
from ..core.CiscoFirepowerManager import CiscoFirepowerManager
from soar_sdk.SiemplifyUtils import construct_csv

INTEGRATION_PROVIDER = "CiscoFirepowerManagementCenter"
SCRIPT_NAME = "CiscoFirepowerManagementCenter_Get Ports List By Name"
CSV_TABLE_HEADER = "{0} Ports List."

# Product's JSON structure.
OBJECTS_KEY = "objects"
PORT_KEY = "port"


@output_handler
def main():

    siemplify = SiemplifyAction()

    # Set script name.
    siemplify.script_name = SCRIPT_NAME

    conf = siemplify.get_configuration(INTEGRATION_PROVIDER)
    verify_ssl = str(conf.get("Verify SSL", "false").lower()) == str(True).lower()

    cisco_firepower_manager = CiscoFirepowerManager(
        conf["API Root"], conf["Username"], conf["Password"], verify_ssl
    )

    result_value = "false"

    # Parameters.
    port_group_name = siemplify.parameters.get("Port Group Name")

    # Get port group object to pass to the block function.
    port_group_object = cisco_firepower_manager.get_port_group_object_by_name(
        port_group_name
    )

    siemplify.result.add_result_json(port_group_object)

    if port_group_object.get(OBJECTS_KEY):
        siemplify.result.add_data_table(
            CSV_TABLE_HEADER.format(port_group_name),
            construct_csv(port_group_object.get(OBJECTS_KEY)),
        )
        output_message = f"Found ports for the following list: {port_group_name}"
        result_value = ",".join(
            [
                address_obj.get(PORT_KEY)
                for address_obj in port_group_object.get(OBJECTS_KEY)
            ]
        )

    else:
        output_message = f"No ports were found for group: {port_group_name}"

    siemplify.end(output_message, result_value)


if __name__ == "__main__":
    main()
