from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyAction import SiemplifyAction
from ..core.PanoramaManager import PanoramaManager
from TIPCommon import extract_configuration_param

SCRIPT_NAME = "Panorama - Ping"
PROVIDER_NAME = "Panorama"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = SCRIPT_NAME
    siemplify.LOGGER.info("================= Main - Param Init =================")

    # Configuration.
    server_address = extract_configuration_param(
        siemplify, provider_name=PROVIDER_NAME, param_name="Api Root"
    )
    username = extract_configuration_param(
        siemplify, provider_name=PROVIDER_NAME, param_name="Username"
    )
    password = extract_configuration_param(
        siemplify, provider_name=PROVIDER_NAME, param_name="Password"
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=PROVIDER_NAME,
        param_name="Verify SSL",
        default_value=True,
        input_type=bool,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    api = PanoramaManager(
        server_address, username, password, verify_ssl, siemplify.run_folder
    )

    output_message = f"Successfully connected to {server_address}"
    result_value = "true"

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Result Value: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.end(output_message, result_value)


if __name__ == "__main__":
    main()
