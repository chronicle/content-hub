from __future__ import annotations

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

from ..core.BitdefenderGravityZoneManager import BitdefenderGravityZoneManager

INTEGRATION_NAME = "BitdefenderGravityZone"
SCRIPT_NAME = "Ping"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = f"{INTEGRATION_NAME} - {SCRIPT_NAME}"
    siemplify.LOGGER.info("================= Main - Param Init =================")

    api_key = siemplify.extract_configuration_param("Integration", "API Key")
    access_url = siemplify.extract_configuration_param("Integration", "Access URL")
    verify_ssl = siemplify.extract_configuration_param(
        "Integration",
        "Verify SSL",
        input_type=bool,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    try:
        siemplify.LOGGER.info("Connecting to Bitdefender GravityZone Control Center.")
        mtm = BitdefenderGravityZoneManager(api_key, verify_ssl)
        apikey_details = mtm.apikey_details(access_url)
        siemplify.LOGGER.info("Connected successfully.")

        output_message = "Connection Established"
        result_value = "true"
        status = EXECUTION_STATE_COMPLETED

        if len(apikey_details) == 0:
            result_value = "false"
            raise ValueError("Please check that your API key is valid.")

    except Exception as e:
        siemplify.LOGGER.error(f"Some errors occurred. Error: {e}")
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        result_value = "false"
        output_message = f"Some errors occurred. Error: {e}"

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}:")
    siemplify.LOGGER.info(f"Result Value: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
