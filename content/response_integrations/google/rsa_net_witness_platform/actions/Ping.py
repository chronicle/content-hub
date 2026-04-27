from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyAction import SiemplifyAction
from ..core.RSAManager import RSAManager
from TIPCommon import extract_configuration_param
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from ..core.constants import INTEGRATION_NAME, PING_ACTION


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = PING_ACTION
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    broker_api_root = extract_configuration_param(
        siemplify, provider_name=INTEGRATION_NAME, param_name="Broker API Root"
    )
    broker_username = extract_configuration_param(
        siemplify, provider_name=INTEGRATION_NAME, param_name="Broker API Username"
    )
    broker_password = extract_configuration_param(
        siemplify, provider_name=INTEGRATION_NAME, param_name="Broker API Password"
    )
    concentrator_api_root = extract_configuration_param(
        siemplify, provider_name=INTEGRATION_NAME, param_name="Concentrator API Root"
    )
    concentrator_username = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Concentrator API Username",
    )
    concentrator_password = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Concentrator API Password",
    )
    ui_api_root = extract_configuration_param(
        siemplify, provider_name=INTEGRATION_NAME, param_name="Web API Root"
    )
    ui_username = extract_configuration_param(
        siemplify, provider_name=INTEGRATION_NAME, param_name="Web Username"
    )
    ui_password = extract_configuration_param(
        siemplify, provider_name=INTEGRATION_NAME, param_name="Web Password"
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        default_value=True,
        input_type=bool,
        is_mandatory=True,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    status = EXECUTION_STATE_COMPLETED
    result_value = True

    try:
        rsa_manager = RSAManager(
            broker_api_root=broker_api_root,
            broker_username=broker_username,
            broker_password=broker_password,
            concentrator_api_root=concentrator_api_root,
            concentrator_username=concentrator_username,
            concentrator_password=concentrator_password,
            ui_api_root=ui_api_root,
            ui_username=ui_username,
            ui_password=ui_password,
            verify_ssl=verify_ssl,
        )
        rsa_manager.test_connectivity()
        output_message = "Connection Established."

    except Exception as e:
        output_message = f"Error executing action {PING_ACTION}. Reason: {e}"
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
