from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyAction import SiemplifyAction
from ..core.SEPManager import SEP14Manager
from TIPCommon import extract_configuration_param

import json


INTEGRATION_NAME = "SEP"


@output_handler
def main():
    siemplify = SiemplifyAction()
    output_message = ""
    result_value = "false"

    conf = siemplify.get_configuration("SEP")
    username = conf["Username"]
    password = conf["Password"]
    domain = conf["Domain"]
    url = conf["Api Root"]
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        input_type=bool,
        default_value=False,
    )
    sep_manager = SEP14Manager(url, username, password, domain, verify_ssl=verify_ssl)

    endpoints = sep_manager.getEndpointList()
    output_message = f"Found {len(endpoints)} endpoints"

    if endpoints:
        csv_output = sep_manager.construct_csv(endpoints)
        siemplify.result.add_data_table("SEP Endpoints", csv_output)

    siemplify.result.add_result_json(endpoints)
    siemplify.end(output_message, json.dumps(endpoints))


if __name__ == "__main__":
    main()
