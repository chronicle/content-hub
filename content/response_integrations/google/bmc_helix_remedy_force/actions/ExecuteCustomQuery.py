from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyAction import SiemplifyAction
from ..core.BMCHelixRemedyForceManager import BMCHelixRemedyForceManager
from TIPCommon import extract_configuration_param, extract_action_param, construct_csv
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from ..core.constants import INTEGRATION_NAME, EXECUTE_CUSTOM_QUERY_ACTION


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = EXECUTE_CUSTOM_QUERY_ACTION

    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Root",
        is_mandatory=True,
        print_value=True,
    )
    login_api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Login API Root",
        is_mandatory=True,
        print_value=True,
    )
    username = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Username",
        print_value=True,
    )
    password = extract_configuration_param(
        siemplify, provider_name=INTEGRATION_NAME, param_name="Password"
    )
    client_id = extract_configuration_param(
        siemplify, provider_name=INTEGRATION_NAME, param_name="Client ID"
    )
    client_secret = extract_configuration_param(
        siemplify, provider_name=INTEGRATION_NAME, param_name="Client Secret"
    )
    refresh_token = extract_configuration_param(
        siemplify, provider_name=INTEGRATION_NAME, param_name="Refresh Token"
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        default_value=True,
        input_type=bool,
        is_mandatory=True,
        print_value=True,
    )

    query = extract_action_param(
        siemplify, param_name="SOQL Query", print_value=True, is_mandatory=True
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    result_value = True
    status = EXECUTION_STATE_COMPLETED

    try:
        manager = BMCHelixRemedyForceManager(
            api_root=api_root,
            password=password,
            username=username,
            verify_ssl=verify_ssl,
            siemplify=siemplify,
            client_id=client_id,
            client_secret=client_secret,
            refresh_token=refresh_token,
            login_api_root=login_api_root,
        )
        query_details = manager.execute_custom_query(query=query)

        if query_details.total_size > 0:
            siemplify.result.add_result_json(query_details.to_json())
            output_message = f'Successfully returned results for the query "{query}" in {INTEGRATION_NAME}.'
            siemplify.result.add_data_table(
                f"Results", data_table=construct_csv(query_details.to_table())
            )
        else:
            output_message = (
                f'No results were found for the query "{query}" in {INTEGRATION_NAME}.'
            )

    except Exception as e:
        output_message = (
            f"Error executing action {EXECUTE_CUSTOM_QUERY_ACTION}. Reason: {e}."
        )
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        result_value = False

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  result_value: {result_value}\n  output_message: {output_message}"
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
