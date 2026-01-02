from __future__ import annotations
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from ..core.APIManager import APIManager
from ..core.constants import PING_SCRIPT_NAME
from ..core.utils import get_integration_params


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = PING_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    # Configuration Parameters
    api_root, api_key, verify_ssl = get_integration_params(siemplify)

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    status = EXECUTION_STATE_COMPLETED
    try:
        infoblox_manager = APIManager(api_root, api_key, verify_ssl=verify_ssl, siemplify=siemplify)
        infoblox_manager.test_connectivity()
        output_message = "Successfully connected to the Infoblox server!"
        connectivity_result = True
        siemplify.LOGGER.info(
            f"Connection to API established, performing action {PING_SCRIPT_NAME}"
        )

    except Exception as e:
        output_message = f"Failed to connect to the Infoblox server! {e}"
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
