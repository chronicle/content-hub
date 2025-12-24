"""Ping Action."""

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

from ..core.ApiManager import ApiManager
from ..core.constants import ERRORS, INTEGRATION_NAME
from ..core.utils import get_integration_params


@output_handler
def main():
    """Test the configuration credentials of the Cylus integration."""
    siemplify = SiemplifyAction()
    siemplify.script_name = f"{INTEGRATION_NAME} - Ping"
    siemplify.LOGGER.info("================= Main - Param Init =================")

    status = EXECUTION_STATE_FAILED
    output_message = ""
    result_value = False

    try:
        siemplify.LOGGER.info("----------------- Main - Started -----------------")

        # Extract integration parameters
        api_root, api_key, verify_ssl = get_integration_params(siemplify)

        # Initialize API manager
        api_manager = ApiManager(api_root, api_key, verify_ssl, siemplify.LOGGER)

        # Test connectivity
        if api_manager.test_connectivity():
            status = EXECUTION_STATE_COMPLETED
            output_message = (
                f"Successfully connected to {INTEGRATION_NAME} with the provided "
                f"connection parameters!"
            )
            result_value = True
        else:
            error_msg = api_manager.error or "Unknown connectivity error"
            status = EXECUTION_STATE_FAILED
            output_message = f"{ERRORS['ACTION']['FAILED']} {error_msg}"
            result_value = False

    except Exception as e:
        siemplify.LOGGER.error(f"❌ Failed to connect to {INTEGRATION_NAME}. Error: {e}")
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        output_message = f"{ERRORS['ACTION']['FAILED']} {str(e)}"
        result_value = False

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"Result Value: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")

    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
