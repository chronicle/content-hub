from __future__ import annotations

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from TIPCommon.extraction import extract_configuration_param

from ..core.constants import GET_OAUTH_TOKEN_SCRIPT_NAME, INTEGRATION_NAME
from ..core.ServiceNowManager import DEFAULT_TABLE, ServiceNowManager


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = GET_OAUTH_TOKEN_SCRIPT_NAME

    result_value = False
    status = EXECUTION_STATE_FAILED

    try:
        api_root = extract_configuration_param(
            siemplify,
            provider_name=INTEGRATION_NAME,
            param_name="Api Root",
            print_value=True,
        )
        username = extract_configuration_param(
            siemplify,
            provider_name=INTEGRATION_NAME,
            param_name="Username",
            print_value=False,
        )
        password = extract_configuration_param(
            siemplify,
            provider_name=INTEGRATION_NAME,
            param_name="Password",
            print_value=False,
        )
        default_incident_table = extract_configuration_param(
            siemplify,
            provider_name=INTEGRATION_NAME,
            param_name="Incident Table",
            print_value=True,
            default_value=DEFAULT_TABLE,
        )
        verify_ssl = extract_configuration_param(
            siemplify,
            provider_name=INTEGRATION_NAME,
            param_name="Verify SSL",
            default_value=True,
            input_type=bool,
        )
        client_id = extract_configuration_param(
            siemplify,
            provider_name=INTEGRATION_NAME,
            param_name="Client ID",
            print_value=False,
        )
        client_secret = extract_configuration_param(
            siemplify,
            provider_name=INTEGRATION_NAME,
            param_name="Client Secret",
            print_value=False,
        )

        siemplify.LOGGER.info("----------------- Main - Started -----------------")

        if not username or not password or not client_id or not client_secret:
            raise Exception(
                '"Client ID", "Client Secret", "Username" and "Password" should be provided.'
            )

        manager = ServiceNowManager(
            api_root=api_root,
            username=username,
            password=password,
            default_incident_table=default_incident_table,
            verify_ssl=verify_ssl,
            siemplify_logger=siemplify.LOGGER,
            client_id=client_id,
            client_secret=client_secret,
        )

        response_json = manager.get_refresh_token()
        # Add json result
        siemplify.result.add_result_json(response_json)
        result_value = True
        status = EXECUTION_STATE_COMPLETED
        output_message = (
            "Successfully generated Oauth tokens for ServiceNow. Now navigate to the configuration tab "
            "and put “refresh_token” value in the “Refresh Token” parameter. Note: “Username” and "
            "“Password” parameters can be emptied."
        )

    except Exception as err:
        output_message = f'Error executing action "{GET_OAUTH_TOKEN_SCRIPT_NAME}". Reason: {err}'
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(err)

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  result_value: {result_value}\n  output_message: {output_message}"
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
