from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyAction import SiemplifyAction
from ..core.CiscoFirepowerManager import CiscoFirepowerManager
from soar_sdk.SiemplifyUtils import construct_csv

INTEGRATION_PROVIDER = "CiscoFirepowerManagementCenter"
SCRIPT_NAME = "CiscoFirepowerManagementCenter_Get URL List By Name"
CSV_TABLE_HEADER = "{0} URLs List."

# Product's JSON structure.
LITERALS_KEY = "literals"
URL_KEY = "url"


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
    url_group_name = siemplify.parameters.get("URL Group Name")

    # Get url group object to pass to the block function.
    url_group_object = cisco_firepower_manager.get_url_group_by_name(url_group_name)

    siemplify.result.add_result_json(url_group_object)

    if url_group_object.get(LITERALS_KEY):
        siemplify.result.add_data_table(
            CSV_TABLE_HEADER.format(url_group_name),
            construct_csv(url_group_object.get(LITERALS_KEY)),
        )
        output_message = f"Found URLs for the following list: {url_group_name}"
        result_value = ",".join(
            [
                address_obj.get(URL_KEY)
                for address_obj in url_group_object.get(LITERALS_KEY)
            ]
        )

    else:
        output_message = f"No URLs were found for group: {url_group_name}"

    siemplify.end(output_message, result_value)


if __name__ == "__main__":
    main()
