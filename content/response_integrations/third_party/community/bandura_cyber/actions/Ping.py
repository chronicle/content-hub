from __future__ import annotations

from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from TIPCommon import extract_configuration_param

from ..core.BanduraCyberManager import BanduraCyberManager

# CONTS
INTEGRATION_NAME = "BanduraCyber"
SCRIPT_NAME = "Ping"


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

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    bandura_cyber_manager = BanduraCyberManager(
        username=username,
        password=password,
        verify_ssl=verify_ssl,
    )

    # Close the session
    bandura_cyber_manager.logout()

    if bandura_cyber_manager.access_token:
        output_message = "Connection Established."
        result_value = "true"
    else:
        output_message = "Connection Failed."

    # End Action
    siemplify.end(output_message, result_value)


if __name__ == "__main__":
    main()
