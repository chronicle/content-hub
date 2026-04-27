from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyAction import SiemplifyAction
from ..core.CuckooManager import CuckooManager
from TIPCommon import extract_configuration_param

INTEGRATION_NAME = "Cuckoo"


@output_handler
def main():
    siemplify = SiemplifyAction()

    server_address = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Api Root",
        is_mandatory=True,
    )
    web_interface_address = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Web Interface Address",
        is_mandatory=True,
    )
    ca_certificate = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="CA Certificate File",
        is_mandatory=False,
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        default_value=False,
        input_type=bool,
        is_mandatory=True,
    )
    api_token = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Token",
        is_mandatory=False,
    )

    cuckoo_manager = CuckooManager(
        server_address, web_interface_address, ca_certificate, verify_ssl, api_token
    )

    result = cuckoo_manager.test_connectivity()

    # If no exception occur - then connection is successful
    output_message = "Connected successfully."

    siemplify.end(output_message, result)


if __name__ == "__main__":
    main()
