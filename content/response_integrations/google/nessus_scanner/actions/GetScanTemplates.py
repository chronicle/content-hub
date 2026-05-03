from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler

# Imports
from soar_sdk.SiemplifyAction import SiemplifyAction
from ..core.NessusScannerManager import NessusScanner

# Consts
TEMPLATE = "Template Name"


@output_handler
def main():
    # Configuration.
    siemplify = SiemplifyAction()
    conf = siemplify.get_configuration("NessusScanner")
    access_key = conf["Access Key"]
    secret_key = conf["Secret Key"]
    server_address = conf["Api Root"]
    nessus_client = NessusScanner(access_key, secret_key, server_address)

    templates_csv = nessus_client.get_scan_templates_csv()
    templates_list = nessus_client.get_scan_templates()
    json_results = {}

    if templates_list:
        json_results["Templates"] = templates_list
    # Verify Result.
    if len(templates_csv) > 1:
        # Display Table.
        siemplify.result.add_data_table("Nessus Scan Templates", templates_csv)
        result_value = "true"
        output_message = "Scan templates were received."
    else:
        result_value = "false"
        output_message = "No scan templates were received."

    siemplify.result.add_result_json = json_results

    siemplify.end(output_message, result_value)


if __name__ == "__main__":
    main()
