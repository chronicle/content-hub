from __future__ import annotations

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

from ..core.EclecticIQManager import EclecticIQManager

INTEGRATION_NAME = "EclecticIQ"
SCRIPT_NAME = "Ping"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = f"{INTEGRATION_NAME} - {SCRIPT_NAME}"
    siemplify.LOGGER.info("================= Main - Param Init =================")

    configs = siemplify.get_configuration(INTEGRATION_NAME)

    eiq_url = configs["EclecticIQ URL"]
    api_token = configs["API Token"]
    verify_ssl = configs["Verify SSL"]
    siemplify.LOGGER.info(str(verify_ssl))

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    try:
        # If no exception occur - then connection is successful
        siemplify.LOGGER.info("Connecting to EclecticIQ.")
        eiq_manager = EclecticIQManager(eiq_url, api_token, verify_ssl)
        eiq_manager.test_connectivity()

        status = EXECUTION_STATE_COMPLETED
        output_message = f"Connected successfully to {eiq_url}"
        siemplify.LOGGER.info(output_message)
        result_value = "true"

    except Exception as e:
        siemplify.LOGGER.error(f"Failed to connect to the EclecticIQ! Error is {e}")
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        result_value = "false"
        output_message = f"Failed to connect to the EclecticIQ! Error is {e}"

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}:")
    siemplify.LOGGER.info(f"Result Value: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
