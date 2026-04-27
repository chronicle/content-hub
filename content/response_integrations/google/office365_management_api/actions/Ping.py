from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from TIPCommon import extract_configuration_param
from ..core.Office365ManagementAPIManager import Office365ManagementAPIManager
from ..core.constants import PROVIDER_NAME, PING_SCRIPT_NAME


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = PING_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    api_root = extract_configuration_param(
        siemplify,
        provider_name=PROVIDER_NAME,
        param_name="Api Root",
        is_mandatory=True,
        print_value=True,
    )
    azure_active_directory_id = extract_configuration_param(
        siemplify,
        provider_name=PROVIDER_NAME,
        param_name="Azure Active Directory ID",
        is_mandatory=True,
        print_value=True,
    )
    client_id = extract_configuration_param(
        siemplify,
        provider_name=PROVIDER_NAME,
        param_name="Client ID",
        is_mandatory=True,
        print_value=True,
    )
    client_secret = extract_configuration_param(
        siemplify,
        provider_name=PROVIDER_NAME,
        param_name="Client Secret",
        is_mandatory=False,
    )

    certificate_path = extract_configuration_param(
        siemplify,
        provider_name=PROVIDER_NAME,
        param_name="Certificate Path",
        is_mandatory=False,
        input_type=str,
    )

    certificate_password = extract_configuration_param(
        siemplify,
        provider_name=PROVIDER_NAME,
        param_name="Certificate Password",
        is_mandatory=False,
        input_type=str,
    )

    oauth2_login_endpoint_url = extract_configuration_param(
        siemplify,
        provider_name=PROVIDER_NAME,
        param_name="OAUTH2 Login Endpoint Url",
        is_mandatory=True,
        print_value=True,
    )

    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=PROVIDER_NAME,
        param_name="Verify SSL",
        is_mandatory=True,
        input_type=bool,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    try:
        Office365ManagementAPIManager(
            api_root=api_root,
            azure_active_directory_id=azure_active_directory_id,
            client_id=client_id,
            client_secret=client_secret,
            oauth2_login_endpoint_url=oauth2_login_endpoint_url,
            verify_ssl=verify_ssl,
            siemplify=siemplify,
            certificate_path=certificate_path,
            certificate_password=certificate_password,
        )
        result = True
        status = EXECUTION_STATE_COMPLETED
        output_message = "Successfully connected to the O365 Management API with the provided connection parameters!"
    except Exception as e:
        result = False
        status = EXECUTION_STATE_FAILED
        output_message = f"Failed to connect to the O365 Management API! Error is {e}"
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"Result: {result}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")

    siemplify.end(output_message, result, status)


if __name__ == "__main__":
    main()
