from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyAction import SiemplifyAction
from ..core.McAfeeTIEDXLManager import McAfeeTIEDXLManager


@output_handler
def main():
    siemplify = SiemplifyAction()
    conf = siemplify.get_configuration("McAfeeTIEDXL")
    server_addr = conf["Server Address"]
    broker_ca_bundle_path = conf["Broker CA Bundle Path"]
    cert_file_path = conf["Client Cert File Path"]
    private_key_path = conf["Client Key File Path"]

    mcafee_dxl_manager = McAfeeTIEDXLManager(
        server_addr, broker_ca_bundle_path, cert_file_path, private_key_path
    )

    # If no exception occur - then connection is successful
    output_message = f"Successfully connected to {server_addr}."
    siemplify.end(output_message, True)


if __name__ == "__main__":
    main()
