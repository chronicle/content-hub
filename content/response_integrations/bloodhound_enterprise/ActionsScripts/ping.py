from __future__ import annotations

from ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from SiemplifyAction import SiemplifyAction
from SiemplifyUtils import output_handler

from bloodhound_manager import BloodhoundManager
from constants import INTEGRATION_NAME, PING_SCRIPT_NAME


@output_handler
def main():
    """
    Main function to perform a connection test (ping) to the BloodHound Enterprise server.

    This script:
    - Extracts configuration parameters: BloodHound Enterprise Server, Token ID, and Token Key.
    - Initializes the BloodHoundManager with the provided credentials.
    - Attempts to establish a connection using the `test_connection()` method.
    - Logs the connection result and ends the script with the appropriate execution state.

    Ends with:
    - EXECUTION_STATE_COMPLETED if the connection was successful.
    - EXECUTION_STATE_FAILED if any exception is raised or configuration is missing.
    """
    siemplify = SiemplifyAction()
    siemplify.script_name = PING_SCRIPT_NAME

    siemplify.LOGGER.info("=============== Main - Param Init ===============")

    # Extract config
    tenant_domain = siemplify.extract_configuration_param(INTEGRATION_NAME, "BloodHound Enterprise Server")
    token_id = siemplify.extract_configuration_param(INTEGRATION_NAME, "Token ID")
    token_key = siemplify.extract_configuration_param(INTEGRATION_NAME, "Token Key")

    if not (tenant_domain and token_id and token_key):
        status = EXECUTION_STATE_FAILED
        siemplify.end("Missing credentials or domain in configuration.", "false", status)
        return

    siemplify.LOGGER.info("=============== Main - Started ===============")

    status = EXECUTION_STATE_COMPLETED
    result_value = True
    output_message = ""

    try:
        bhe_manager = BloodhoundManager(tenant_domain, token_id, token_key, logger=siemplify.LOGGER)

        siemplify.LOGGER.info(f"Connecting to {INTEGRATION_NAME}")
        bhe_manager.test_connection()
        output_message = (
            f"Successfully connected to the {INTEGRATION_NAME} server "
            f"with the provided connection parameters!"
        )

    except Exception as error:
        result_value = False
        status = EXECUTION_STATE_FAILED
        output_message = f"Failed to connect to the {INTEGRATION_NAME} server! Error is {error}"
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(error)

    siemplify.LOGGER.info("=============== Main - Finished ===============")
    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"Result Value: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")

    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()