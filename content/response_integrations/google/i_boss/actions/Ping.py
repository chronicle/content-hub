from __future__ import annotations
from soar_sdk.SiemplifyAction import SiemplifyAction
from ..core.IBossManager import IBossManager
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from TIPCommon import extract_configuration_param
from ..core.constants import PING_SCRIPT_NAME, INTEGRATION_NAME


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = PING_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    cloud_api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Cloud API Root",
        is_mandatory=True,
    )
    account_api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Account API Root",
        is_mandatory=True,
    )
    username = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Username",
        is_mandatory=True,
    )
    password = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Password",
        is_mandatory=True,
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        default_value=True,
        input_type=bool,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    status = EXECUTION_STATE_FAILED
    connectivity_result = False
    try:
        manager = IBossManager(
            cloud_api_root,
            account_api_root,
            username,
            password,
            verify_ssl,
            siemplify.LOGGER,
        )
        manager.test_connectivity()
        output_message = (
            "Successfully connected to the IBoss server with the provided connection "
            "parameters!"
        )
        siemplify.LOGGER.info(output_message)
        connectivity_result = True
        status = EXECUTION_STATE_COMPLETED
    except Exception as e:
        output_message = f"Failed to connect to the IBoss server! Error is {e}"
        siemplify.LOGGER.error(
            f"Connection to API failed, performing action {PING_SCRIPT_NAME}"
        )
        siemplify.LOGGER.exception(e)

    siemplify.end(output_message, connectivity_result, status)


if __name__ == "__main__":
    main()
