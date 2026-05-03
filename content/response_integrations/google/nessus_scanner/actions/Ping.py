from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler

# Imports
from soar_sdk.SiemplifyAction import SiemplifyAction
from ..core.NessusScannerManager import NessusScanner


@output_handler
def main():
    siemplify = SiemplifyAction()

    # Configuration.
    conf = siemplify.get_configuration("NessusScanner")
    access_key = conf["Access Key"]
    secret_key = conf["Secret Key"]
    server_address = conf["Api Root"]
    nessus_client = NessusScanner(access_key, secret_key, server_address)

    # Execute Test Connectivity.
    server_status = nessus_client.test_connectivity()

    if server_status:
        output_message = "Connection Established."
        result_value = "true"
    else:
        output_message = "Connection Failed."
        result_value = "false"

    siemplify.end(output_message, result_value)


if __name__ == "__main__":
    main()
