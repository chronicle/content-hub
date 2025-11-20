"""Ping Action."""

from __future__ import annotations

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

from ..core.ApiManager import ApiManager
from ..core.constants import ERRORS, INTEGRATION_NAME
from ..core.utils import get_integration_params
from ..core.XMCyberException import XMCyberException


@output_handler
def main():
    """Test the configuration credentials of the XMCyber integration."""
    is_success = False
    response = ""
    output_message = ""
    status = EXECUTION_STATE_FAILED

    siemplify = SiemplifyAction()
    auth_type, base_url, api_key = get_integration_params(siemplify)
    try:
        api_manager = ApiManager(auth_type, base_url, api_key, siemplify)
        if api_manager.error:
            raise XMCyberException(api_manager.error)

        is_success = True

    except Exception as e:
        response = str(e)

    if is_success is True:
        status = EXECUTION_STATE_COMPLETED
        output_message = (
            f"Successfully connected to the {INTEGRATION_NAME} server with the provided "
            f"connection parameters."
        )
    else:
        status = EXECUTION_STATE_FAILED
        output_message = f"{ERRORS['ACTION']['FAILED']} {response}"

    result_value = is_success

    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"Result: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")

    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
