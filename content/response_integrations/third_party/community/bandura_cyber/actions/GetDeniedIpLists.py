from __future__ import annotations

import json

from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyUtils import construct_csv, output_handler
from TIPCommon import extract_action_param, extract_configuration_param

from ..core.BanduraCyberManager import BanduraCyberManager

# CONTS
INTEGRATION_NAME = "BanduraCyber"
SCRIPT_NAME = "Get Denied IP Lists"
ADDRESS = EntityTypes.ADDRESS


@output_handler
def main():
    json_results = {}
    entities_with_results = []
    result_value = False

    # Configuration.
    siemplify = SiemplifyAction()
    siemplify.script_name = f"{INTEGRATION_NAME} - {SCRIPT_NAME}"
    siemplify.LOGGER.info("================= Main - Param Init =================")

    # INIT INTEGRATION CONFIGURATION:
    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Root",
        is_mandatory=True,
        input_type=str,
    )
    username = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Username",
        is_mandatory=True,
        input_type=str,
    )
    password = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Password",
        is_mandatory=True,
        input_type=str,
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        default_value=False,
        input_type=bool,
    )

    list_name = extract_action_param(
        siemplify,
        param_name="List Name",
        is_mandatory=False,
        input_type=str,
        print_value=True,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    bandura_cyber_manager = BanduraCyberManager(
        username=username,
        password=password,
        verify_ssl=verify_ssl,
    )

    results = bandura_cyber_manager.show_denied_ip_list(list_name=list_name)

    # Close the session
    bandura_cyber_manager.logout()

    if results:
        # Add original json as attachment
        siemplify.result.add_attachment(
            "Bandura Denied IP Lists Output",
            "denied_ip_lists.txt",
            json.dumps(results),
        )

        # Add data table
        siemplify.result.add_data_table(
            "Bandura Denied IP Lists",
            construct_csv(results),
        )

        siemplify.result.add_result_json(results)
        output_message = "Following Denied IP Lists were found.\n"
        result_value = True
    else:
        output_message = "No Denied IP Lists were found."
        result_value = False

    siemplify.end(output_message, result_value)


if __name__ == "__main__":
    main()
