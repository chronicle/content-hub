from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyAction import SiemplifyAction
from ..core.CiscoISEManager import CiscoISEManager
from TIPCommon import extract_configuration_param

INTEGRATION_NAME = "CiscoISE"


@output_handler
def main():
    # Configuration.
    siemplify = SiemplifyAction()
    siemplify.script_name = "CiscoISE_Ping"
    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Root",
        print_value=True,
    )
    username = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Username",
        print_value=True,
    )
    password = extract_configuration_param(
        siemplify, provider_name=INTEGRATION_NAME, param_name="Password"
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        input_type=bool,
        print_value=True,
    )

    cim = CiscoISEManager(api_root, username, password, verify_ssl)

    # Test regular API.
    result_value = cim.ping()

    if result_value:
        output_message = "Connection Established."
    else:
        output_message = "Connection Failed."

    siemplify.end(output_message, result_value)


if __name__ == "__main__":
    main()
