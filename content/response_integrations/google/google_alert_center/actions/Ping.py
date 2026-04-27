from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from TIPCommon import extract_configuration_param
from ..core.GoogleAlertCenterManager import GoogleAlertCenterManager
from ..core.constants import INTEGRATION_NAME, INTEGRATION_DISPLAY_NAME, PING_SCRIPT_NAME
from ..core.GoogleAlertCenterExceptions import GoogleAlertCenterInvalidJsonException


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = PING_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    service_account_json_secret = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Service Account JSON Secret",
        is_mandatory=True,
    )

    impersonation_email_address = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Impersonation Email Address",
        is_mandatory=True,
    )

    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        is_mandatory=True,
        input_type=bool,
        print_value=True,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    result = False
    status = EXECUTION_STATE_FAILED

    try:
        manager = GoogleAlertCenterManager(
            service_account_json_secret=service_account_json_secret,
            impersonation_email_address=impersonation_email_address,
            verify_ssl=verify_ssl,
            siemplify=siemplify,
        )

        manager.test_connectivity()
        result = True
        status = EXECUTION_STATE_COMPLETED
        output_message = (
            f"Successfully connected to the {INTEGRATION_DISPLAY_NAME} server with the provided "
            f"connection parameters!"
        )

    except GoogleAlertCenterInvalidJsonException:
        output_message = (
            'Invalid JSON payload provided in the parameter "Service Account JSON Secret". Please '
            "check the structure."
        )

    except Exception as e:
        siemplify.LOGGER.error(f"General error performing action {PING_SCRIPT_NAME}")
        siemplify.LOGGER.exception(e)
        output_message = (
            f"Failed to connect to the {INTEGRATION_DISPLAY_NAME} server! Error is {e}"
        )

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"Result: {result}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")

    siemplify.end(output_message, result, status)


if __name__ == "__main__":
    main()
