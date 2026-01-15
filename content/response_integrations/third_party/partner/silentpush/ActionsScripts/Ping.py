from SiemplifyAction import SiemplifyAction
from SiemplifyUtils import unix_now, convert_unixtime_to_datetime, output_handler
from ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED,EXECUTION_STATE_TIMEDOUT

from constants import (INTEGRATION_NAME, PING_SCRIPT_NAME)
from SilentPushManager import SilentPushManager

@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = PING_SCRIPT_NAME

    siemplify.LOGGER.info("=============== Main - Param Init ===============")

    # Extract config
    server_url = siemplify.extract_configuration_param(INTEGRATION_NAME, "Silent Push Server")
    api_key = siemplify.extract_configuration_param(INTEGRATION_NAME, "API Key")

    if not (server_url and api_key):
        status = EXECUTION_STATE_FAILED
        siemplify.end("Missing credentials or api_key in configuration.", "false", status)
        return

    siemplify.LOGGER.info("=============== Main - Started ===============")

    status = EXECUTION_STATE_COMPLETED
    result_value = True
    output_message = ""

    try:
        sp_manager = SilentPushManager(server_url, api_key, logger=siemplify.LOGGER)

        siemplify.LOGGER.info(f"Connecting to {INTEGRATION_NAME}...\n")
        sp_manager.test_connection()
        output_message = f"Successfully connected to the {INTEGRATION_NAME} server with the provided connection parameters!"

    except Exception as error:
        result_value = False
        status = EXECUTION_STATE_FAILED
        output_message = f"Failed to connect to the {INTEGRATION_NAME} server! Error: {error}"
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(error)

    siemplify.LOGGER.info("=============== Main - Finished ===============")
    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"Result Value: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")

    siemplify.end(output_message, result_value, status)



if __name__ == "__main__":
    main()


