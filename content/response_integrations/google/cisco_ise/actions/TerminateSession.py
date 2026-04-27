from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyAction import SiemplifyAction
from ..core.CiscoISEManager import CiscoISEManager
from TIPCommon import extract_configuration_param, extract_action_param

INTEGRATION_NAME = "CiscoISE"


@output_handler
def main():
    # Configuration.
    siemplify = SiemplifyAction()
    siemplify.script_name = "CiscoISE_Terminate Session"

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

    # Parameters.
    node_server_name = extract_action_param(
        siemplify, param_name="Node Server Name", print_value=True
    )
    calling_station_id = extract_action_param(
        siemplify, param_name="Calling Station ID", print_value=True
    )
    terminate_type = extract_action_param(
        siemplify,
        param_name="Terminate Type",
        print_value=True,
        input_type=int,
        default_value=0,
    )

    result_value = cim.terminate_session(
        node_server_name, calling_station_id, terminate_type
    )

    if result_value:
        output_message = "Session terminated."
    else:
        output_message = "Session was not terminated."

    siemplify.end(output_message, result_value)


if __name__ == "__main__":
    main()
