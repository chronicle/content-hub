from __future__ import annotations
from TIPCommon import extract_configuration_param, extract_action_param
from ..core.BMCHelixRemedyForceManager import BMCHelixRemedyForceManager
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from ..core.constants import INTEGRATION_NAME, GENERATE_TOKEN_SCRIPT_NAME


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = f"{INTEGRATION_NAME} - {GENERATE_TOKEN_SCRIPT_NAME}"
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    # INTEGRATION Configuration
    client_id = extract_configuration_param(
        siemplify, provider_name=INTEGRATION_NAME, param_name="Client ID"
    )
    client_secret = extract_configuration_param(
        siemplify, provider_name=INTEGRATION_NAME, param_name="Client Secret"
    )
    login_api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Login API Root",
        is_mandatory=True,
        print_value=True,
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
        response_json = BMCHelixRemedyForceManager.obtain_refresh_token(
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri=redirect_url,
            code=authorization_code,
            login_api_root=login_api_root,
        )
        siemplify.result.add_result_json(response_json)
        output_message = (
            f"Successfully generated refresh token in BMC Helix Remedyforce."
        )
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
