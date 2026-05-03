from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyAction import SiemplifyAction
from ..core.CiscoFirepowerManager import CiscoFirepowerManager
from soar_sdk.SiemplifyUtils import construct_csv

INTEGRATION_PROVIDER = "CiscoFirepowerManagementCenter"
SCRIPT_NAME = "CiscoFirepowerManagementCenter_Get Addresses List By Name"
CSV_TABLE_HEADER = "{0} Addresses List."

# Product's JSON structure.
LITERALS_KEY = "literals"
VALUE_KEY = "value"


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
    network_group_name = siemplify.parameters.get("Network Group Name")

    # Get url group object to pass to the block function.
    network_group_object = cisco_firepower_manager.get_network_group_object_by_name(
        network_group_name
    )

    siemplify.result.add_result_json(network_group_object)

    if network_group_object.get(LITERALS_KEY):
        siemplify.result.add_data_table(
            CSV_TABLE_HEADER.format(network_group_name),
            construct_csv(network_group_object.get(LITERALS_KEY)),
        )
        output_message = f"Found addresses for the following list: {network_group_name}"
        result_value = ",".join(
            [
                address_obj.get(VALUE_KEY)
                for address_obj in network_group_object.get(LITERALS_KEY)
            ]
        )

    else:
        output_message = f"No addresses were found for group: {network_group_name}"

    siemplify.end(output_message, result_value)


if __name__ == "__main__":
    main()
