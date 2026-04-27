from __future__ import annotations
from TIPCommon import extract_configuration_param, extract_action_param
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from ..core.constants import INTEGRATION_NAME, GET_AUTHORIZATION_SCRIPT_NAME

AUTHORIZATION_URL = "{api_root}/services/oauth2/authorize?response_type=code&client_id={client_id}&redirect_uri={redirect_uri}"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = f"{INTEGRATION_NAME} - {GET_AUTHORIZATION_SCRIPT_NAME}"
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    # INTEGRATION Configuration
    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Root",
        is_mandatory=True,
        print_value=True,
    )
    client_id = extract_configuration_param(
        siemplify, provider_name=INTEGRATION_NAME, param_name="Client ID"
    )

    # Action configuration
    redirect_url = extract_action_param(
        siemplify, param_name="Redirect URL", is_mandatory=True, print_value=True
    )
    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    try:
        auth_link = AUTHORIZATION_URL.format(
            api_root=api_root, client_id=client_id, redirect_uri=redirect_url
        )
        siemplify.result.add_link("Authorization Code Link", auth_link)
        output_message = (
            "Successfully generated Authorization code URL in BMC Helix Remedyforce. "
            'Please copy paste it in the browser. After that, copy the "code" part from the URL. '
            'This authorization code is used in action "Get OAuth Refresh Token".'
        )
        status = EXECUTION_STATE_COMPLETED
        result_value = True
    except Exception as error:
        output_message = (
            f"Error executing action {GET_AUTHORIZATION_SCRIPT_NAME}. Reason: {error}"
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
