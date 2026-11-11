from __future__ import annotations
import json
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyAction import SiemplifyAction
from splunk.core.SplunkManager import SplunkManager
from TIPCommon.extraction import extract_configuration_param, extract_action_param
from TIPCommon.transformation import construct_csv
from splunk.core.constants import INTEGRATION_NAME


@output_handler
def main():
    siemplify = SiemplifyAction()

    siemplify.script_name = "Splunk - SplunkCsvViewer"

    url = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Api Root",
        print_value=True,
    )
    username = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Username",
        print_value=False,
    )
    password = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Password",
        print_value=False,
    )
    api_token = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Token",
        print_value=False,
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        print_value=True,
        input_type=bool,
    )
    ca_certificate = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="CA Certificate File",
        print_value=False,
    )

    SplunkManager(
        server_address=url,
        username=username,
        password=password,
        api_token=api_token,
        ca_certificate=ca_certificate,
        verify_ssl=verify_ssl,
        siemplify_logger=siemplify.LOGGER,
    )

    results = extract_action_param(
        siemplify, param_name="Results", print_value=True, is_mandatory=True
    )

    if results:
        results = json.loads(results)
        csv_output = construct_csv(results)
        siemplify.result.add_data_table("Splunk Query Results", csv_output)

    output_message = "Results were found" if results else "No Results were found"
    result_value = "true" if results else "false"
    siemplify.end(output_message, result_value)


if __name__ == "__main__":
    main()
