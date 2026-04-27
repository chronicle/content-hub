from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from ..core.Dome9Manager import Dome9Manager
from TIPCommon import extract_configuration_param


INTEGRATION_NAME = "CheckPointCloudGuard"
SCRIPT_NAME = "Ping"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = f"{INTEGRATION_NAME} - {SCRIPT_NAME}"
    siemplify.LOGGER.info("================= Main - Param Init =================")

    # INIT INTEGRATION CONFIGURATION:
    api_key_id = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Key ID",
        is_mandatory=True,
    )
    api_key_secret = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Key Secret",
        is_mandatory=True,
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        default_value=False,
        input_type=bool,
    )
    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    try:
        dome_manager = Dome9Manager(
            api_key_id=api_key_id, api_key_secret=api_key_secret, verify_ssl=verify_ssl
        )
        dome_manager.test_connectivity()
        status = EXECUTION_STATE_COMPLETED
        output_message = ("Successfully connected to the Check Point Cloud Guard "
                          "server with the provided connection parameters!")
        result_value = "true"

    except Exception as e:
        siemplify.LOGGER.error(
            f"Failed to connect to the Check Point Cloud Guard server! Error is {e}"
        )
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        result_value = "false"
        output_message = (f"Failed to connect to the Check Point Cloud Guard server! "
                          f"Error is {e}")

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}:")
    siemplify.LOGGER.info(f"Result Value: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
