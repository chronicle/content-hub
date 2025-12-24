from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

from ..core.constants import (
    THINKST_DEFAULT_API_KEY,
    THINKST_DEFAULT_CONSOLE,
    THINKST_INTEGRATION_NAME,
)
from ..core.thinkst_manager import ThinkstActionManager, str_to_bool


@output_handler
def main():
    status = EXECUTION_STATE_COMPLETED
    result_value = False
    output_message = ""

    siemplify = SiemplifyAction()

    console_api_key = siemplify.extract_configuration_param(
        provider_name=THINKST_INTEGRATION_NAME,
        param_name="API Key",
        default_value=THINKST_DEFAULT_API_KEY,
    )
    if console_api_key == THINKST_DEFAULT_API_KEY:
        status = EXECUTION_STATE_FAILED
        output_message = "Please provide a valid API Key"
        siemplify.end(output_message, result_value, status)
        return

    console_hash = siemplify.extract_configuration_param(
        provider_name=THINKST_INTEGRATION_NAME,
        param_name="Console Hash",
        default_value=THINKST_DEFAULT_CONSOLE,
    )
    if console_hash == THINKST_DEFAULT_CONSOLE:
        status = EXECUTION_STATE_FAILED
        output_message = "Please provide a valid Console Hash"
        siemplify.end(output_message, result_value, status)
        return

    ssl_verify = siemplify.extract_configuration_param(
        provider_name=THINKST_INTEGRATION_NAME, param_name="Verify SSL"
    )

    try:
        ssl = str_to_bool(ssl_verify)
        manager = ThinkstActionManager(console_api_key, console_hash, siemplify, ssl)
        ping_res = manager.ping()

        if ping_res:
            output_message = f"Successfully connected to Canary Console '{console_hash}'."
            result_value = True
        else:
            output_message = f"Failed to connect to Canary Console '{console_hash}'."

    except Exception as e:
        status = EXECUTION_STATE_FAILED
        output_message = f"Ping failed: {str(e)}"
        siemplify.LOGGER.exception(e)

    siemplify.LOGGER.info(f"Action finished: {output_message}")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
