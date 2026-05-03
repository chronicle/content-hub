from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler

# Imports
from soar_sdk.SiemplifyAction import SiemplifyAction
from ..core.NessusScannerManager import NessusScanner


@output_handler
def main():
    # Configuration.
    siemplify = SiemplifyAction()
    conf = siemplify.get_configuration("NessusScanner")
    access_key = conf["Access Key"]
    secret_key = conf["Secret Key"]
    server_address = conf["Api Root"]
    nessus_client = NessusScanner(access_key, secret_key, server_address)

    scans_csv = nessus_client.get_scans_name_csv()
    scans_list = nessus_client.get_scans()
    json_results = {}

    if scans_list:
        json_results["Scans"] = scans_list
    # Verify Result.
    if scans_csv:
        # Display Table.
        siemplify.result.add_data_table("Nessus Scans", scans_csv)
        result_value = "true"
        output_message = "Attached Nessus Scans"
    else:
        result_value = "false"
        output_message = "No scans were found."

    siemplify.result.add_result_json = json_results

    siemplify.end(output_message, result_value)


if __name__ == "__main__":
    main()
