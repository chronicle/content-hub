from __future__ import annotations

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

from ..core.ApiManager import ApiManager
from ..core.constants import INTEGRATION_NAME, PING_SCRIPT_NAME
from ..core.utils import get_integration_params


@output_handler
def main():
    """Ping action is used to Test the configuration of the Team Cymru Scout integration"""
    siemplify = SiemplifyAction()

    auth_type, api_key, username, password, verify_ssl = get_integration_params(
        siemplify,
    )

    try:
        api_manager = ApiManager(
            auth_type,
            api_key,
            username,
            password,
            siemplify.LOGGER,
            verify_ssl,
        )

        is_success, response = api_manager.api_usage()
    except Exception as e:
        is_success = False
        response = str(e)

    if is_success is True:
        status = EXECUTION_STATE_COMPLETED
        output_message = f"Successfully connected to the {INTEGRATION_NAME} server with the provided connection parameters."
    else:
        siemplify.LOGGER.error(
            f"Error occurred while performing action: {PING_SCRIPT_NAME}",
        )
        siemplify.LOGGER.exception(response)

        status = EXECUTION_STATE_FAILED
        output_message = (
            f"Failed to connect to the {INTEGRATION_NAME} server! Error: {response}"
        )

    result_value = is_success

    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"Result: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")

    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
