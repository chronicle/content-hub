from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyAction import SiemplifyAction
from ..core.StealthwatchManager import StealthwatchManager
from TIPCommon import extract_configuration_param

INTEGRATION_NAME = "Stealthwatch"


@output_handler
def main():
    siemplify = SiemplifyAction()
    configurations = siemplify.get_configuration("Stealthwatch")
    server_address = configurations["Api Root"]
    username = configurations["Username"]
    password = configurations["Password"]
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        input_type=bool,
        default_value=False,
    )

    stealthwatch_manager = StealthwatchManager(
        server_address, username, password, verify_ssl
    )

    connectivity = stealthwatch_manager.test_connectivity()
    output_message = "Connected Successfully"
    siemplify.end(output_message, connectivity)


if __name__ == "__main__":
    main()
