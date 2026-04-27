from __future__ import annotations
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED

from TIPCommon import extract_configuration_param

from ..core.McAfeeMvisionEDRManager import McAfeeMvisionEDRManager
from ..core.constants import PROVIDER_NAME

SCRIPT_NAME = "McAfeeMvisionEDR - Ping"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    api_root = extract_configuration_param(
        siemplify, provider_name=PROVIDER_NAME, param_name="API Root", input_type=str
    )
    login_api_root = extract_configuration_param(
        siemplify,
        provider_name=PROVIDER_NAME,
        param_name="Login API Root",
        input_type=str,
    )
    username = extract_configuration_param(
        siemplify, provider_name=PROVIDER_NAME, param_name="Username", input_type=str
    )
    password = extract_configuration_param(
        siemplify, provider_name=PROVIDER_NAME, param_name="Password", input_type=str
    )
    client_id = extract_configuration_param(
        siemplify, provider_name=PROVIDER_NAME, param_name="Client ID", input_type=str
    )
    client_secret = extract_configuration_param(
        siemplify,
        provider_name=PROVIDER_NAME,
        param_name="Client Secret",
        input_type=str,
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=PROVIDER_NAME,
        param_name="Verify SSL",
        default_value=False,
        input_type=bool,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    status = EXECUTION_STATE_COMPLETED
    try:
        mvision_edr_manager = McAfeeMvisionEDRManager(
            api_root,
            username,
            password,
            client_id,
            client_secret,
            verify_ssl=verify_ssl,
            login_api_root=login_api_root,
        )
        mvision_edr_manager.test_connectivity()
        output_message = "Successfully connected to the McAfee Mvision EDR server with the provided connection parameters!"
        connectivity_result = True
        siemplify.LOGGER.info(
            f"Connection to API established, performing action {SCRIPT_NAME}"
        )

    except Exception as e:
        output_message = (
            f"Failed to connect to the McAfee Mvision EDR server! Error is {e}"
        )
        connectivity_result = False
        siemplify.LOGGER.error(
            f"Connection to API failed, performing action {SCRIPT_NAME}"
        )

        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED

    siemplify.end(output_message, connectivity_result, status)


if __name__ == "__main__":
    main()
