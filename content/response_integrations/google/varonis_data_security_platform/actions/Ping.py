from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.ScriptResult import EXECUTION_STATE_FAILED, EXECUTION_STATE_COMPLETED
from TIPCommon import extract_configuration_param

from ..core.VaronisDataSecurityPlatformManager import VaronisDataSecurityPlatformManager
from ..core.VaronisDataSecurityPlatformConstants import INTEGRATION_IDENTIFIER


@output_handler
def main():
    siemplify = SiemplifyAction()

    # Configuration.
    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_IDENTIFIER,
        param_name="API Root",
        is_mandatory=True,
        print_value=True,
    )
    username = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_IDENTIFIER,
        param_name="Username",
        is_mandatory=True,
        print_value=True,
    )
    password = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_IDENTIFIER,
        param_name="Password",
        is_mandatory=True,
        remove_whitespaces=False,
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_IDENTIFIER,
        param_name="Verify SSL",
        is_mandatory=True,
        print_value=True,
        input_type=bool,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    try:
        siemplify.LOGGER.info("Connecting to Varonis Data Security Platform.")
        VaronisDataSecurityPlatformManager(
            api_root=api_root,
            username=username,
            password=password,
            verify_ssl=verify_ssl,
        )
        siemplify.LOGGER.info("Connected successfully.")

        output_message = (
            "Successfully connected to the Varonis Data Security Platform "
            "with the provided connection parameters!"
        )
        result_value = "true"
        status = EXECUTION_STATE_COMPLETED

    except Exception as e:
        log_message = (
            f"Failed to connect to the Varonis Data Security Platform! Error is {e}"
        )
        siemplify.LOGGER.error(log_message)
        siemplify.LOGGER.exception(e)
        output_message = log_message
        result_value = "false"
        status = EXECUTION_STATE_FAILED

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}:")
    siemplify.LOGGER.info(f"Result Value: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
