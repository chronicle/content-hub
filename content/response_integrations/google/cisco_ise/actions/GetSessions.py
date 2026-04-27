from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyAction import SiemplifyAction
from ..core.CiscoISEManager import CiscoISEManager
from TIPCommon import dict_to_flat, construct_csv, extract_configuration_param

INTEGRATION_NAME = "CiscoISE"
TABLE_HEADER = "Sessions"


@output_handler
def main():
    # Configuration.
    siemplify = SiemplifyAction()
    siemplify.script_name = "CiscoISE_GetSessions"
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

    # Variables.
    result_value = False

    session_list = cim.get_sessions()
    if session_list:
        csv = construct_csv(list(map(dict_to_flat, session_list)))
        siemplify.result.add_data_table(TABLE_HEADER, csv)
        result_value = True
        output_message = f'Found "{len(session_list)}" active sessions.'
    else:
        output_message = "No active sessions found."

    siemplify.end(output_message, result_value)


if __name__ == "__main__":
    main()
