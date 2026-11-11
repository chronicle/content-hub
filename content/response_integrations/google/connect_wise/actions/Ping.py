from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler

# Imports
from soar_sdk.SiemplifyAction import SiemplifyAction
from connect_wise.core.ConnectWiseManager import ConnectWiseManager


@output_handler
def main():
    siemplify = SiemplifyAction()
    # Configuration.
    configuration_settings = siemplify.get_configuration("ConnectWise")
    company_url = configuration_settings["Api Root"]
    company_name = configuration_settings["Company Name"]
    public_key = configuration_settings["Public Key"]
    private_key = configuration_settings["Private Key"]
    client_id = configuration_settings["Client Id"]
    connectwise_manager = ConnectWiseManager(
        company_url, company_name, public_key, private_key, client_id
    )

    # Execute Test Connectivity.
    result = connectwise_manager.test_connectivity()

    if result:
        output_message = "Connection Established."
        result_value = True
    else:
        output_message = "Connection Failed."
        result_value = False

    siemplify.end(output_message, result_value)


if __name__ == "__main__":
    main()
