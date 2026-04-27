from __future__ import annotations
from ..core.CynetManager import CynetManager
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from TIPCommon import extract_configuration_param

INTEGRATION_NAME = "Cynet"


@output_handler
def main():
    siemplify = SiemplifyAction()
    output_message = ""
    result_value = False

    # Configuration.
    conf = siemplify.get_configuration("Cynet")
    api_root = conf["Api Root"]
    username = conf["Username"]
    password = conf["Password"]
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        default_value=False,
        input_type=bool,
    )
    cynet_manager = CynetManager(api_root, username, password, verify_ssl)

    if cynet_manager:
        output_message = "Connection Established."
        result_value = True
    else:
        output_message = "Connection Failed."

    siemplify.end(output_message, result_value)


if __name__ == "__main__":
    main()
