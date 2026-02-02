from __future__ import annotations

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

from ..core.api_manager import APIManager
from ..core.constants import PING_SCRIPT_NAME
from ..core.utils import get_integration_params


@output_handler
def main():
    """Test connectivity to Rubrik Security Cloud.

    This action performs a simple connectivity test to verify that the integration
    can successfully authenticate and communicate with the Rubrik Security Cloud API.

    Returns:
        None. Results are returned via siemplify.end() with:
            - output_message (str): Status message describing the connectivity test result
            - connectivity_result (bool): True if connection successful, False otherwise
            - status (str): Execution state (COMPLETED or FAILED)

    Raises:
        Exception: If connectivity test fails for any reason
    """
    siemplify = SiemplifyAction()
    siemplify.script_name = PING_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    # Configuration Parameters
    service_account_json, verify_ssl = get_integration_params(siemplify)

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    status = EXECUTION_STATE_COMPLETED
    try:
        rubrik_manager = APIManager(
            service_account_json,
            verify_ssl=verify_ssl,
            siemplify=siemplify,
        )
        rubrik_manager.test_connectivity()
        output_message = "Successfully connected to the Rubrik Security Cloud server!"
        connectivity_result = True
        siemplify.LOGGER.info(
            f"Connection to API established, performing action {PING_SCRIPT_NAME}"
        )

    except Exception as e:
        output_message = f"Failed to connect to the Rubrik Security Cloud server! {e}"
        connectivity_result = False
        siemplify.LOGGER.error(f"Connection to API failed, performing action {PING_SCRIPT_NAME}")
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"result_value: {connectivity_result}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.end(output_message, connectivity_result, status)


if __name__ == "__main__":
    main()
