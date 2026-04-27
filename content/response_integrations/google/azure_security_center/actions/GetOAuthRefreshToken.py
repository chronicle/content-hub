from __future__ import annotations
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

from TIPCommon.extraction import extract_action_param, extract_configuration_param

from ..core.AzureSecurityCenterManager import AzureSecurityCenterManager
from ..core.consts import INTEGRATION_NAME, GENERATE_TOKEN_SCRIPT_NAME


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = GENERATE_TOKEN_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    # INTEGRATION Configuration
    tenant_id = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Tenant ID",
        is_mandatory=True,
        print_value=True,
    )
    client_id = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Client ID",
        is_mandatory=True,
        print_value=True,
    )
    client_secret = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Client Secret",
        is_mandatory=True,
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        default_value=False,
        input_type=bool,
        is_mandatory=True,
    )

    # Action configuration
    redirect_url = extract_action_param(
        siemplify, param_name="Redirect URL", is_mandatory=True, print_value=True
    )
    authorization_code = extract_action_param(
        siemplify, param_name="Authorization Code", is_mandatory=True, print_value=True
    )
    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    try:
        response_json = AzureSecurityCenterManager.obtain_refresh_token(
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri=redirect_url,
            code=authorization_code,
            tenant_id=tenant_id,
            verify_ssl=verify_ssl,
        )
        siemplify.result.add_result_json(response_json)
        output_message = f"Successfully generated refresh token in {INTEGRATION_NAME}."
        status = EXECUTION_STATE_COMPLETED
        result_value = True
    except Exception as error:
        output_message = (
            f"Error executing action {GENERATE_TOKEN_SCRIPT_NAME}. Reason: {error}"
        )
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(error)
        status = EXECUTION_STATE_FAILED
        result_value = False

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"Result Value: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
