from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyAction import SiemplifyAction
from ..core.SSLLabsManager import SSLLabsManager
from TIPCommon import extract_configuration_param

INTEGRATION_NAME = "SSLLabs"


@output_handler
def main():
    siemplify = SiemplifyAction()
    warning_threshold = extract_configuration_param(
        siemplify, provider_name=INTEGRATION_NAME, param_name="Warning Threshold"
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        input_type=bool,
        default_value=False,
    )

    ssl_labs_manager = SSLLabsManager(verify_ssl)
    ssl_labs_manager.test_connectivity()

    # If no exception occurs - then connection is successful.
    siemplify.end("Connected successfully.", "true")


if __name__ == "__main__":
    main()
