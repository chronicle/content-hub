from __future__ import annotations

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

from ..core.api_manager import APIManager
from ..core.constants import (
    COMMON_ACTION_ERROR_MESSAGE,
    PING_SCRIPT_NAME,
    RESULT_VALUE_FALSE,
    RESULT_VALUE_TRUE,
)
from ..core.utils import get_integration_params


@output_handler
def main() -> None:
    siemplify = SiemplifyAction()
    siemplify.script_name = PING_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    output_message = ""
    status = EXECUTION_STATE_COMPLETED
    connectivity_result = RESULT_VALUE_FALSE

    try:
        base_url, access_id, secret_key, verify_ssl = get_integration_params(siemplify)

        siemplify.LOGGER.info("----------------- Main - Started -----------------")

        cyware_manager = APIManager(
            base_url.strip(), access_id, secret_key, verify_ssl=verify_ssl, siemplify=siemplify
        )
        cyware_manager.test_connectivity()
        output_message = "Successfully connected to the Cyware server!"
        connectivity_result = RESULT_VALUE_TRUE
        siemplify.LOGGER.info(
            f"Connection to API established, performing action {PING_SCRIPT_NAME}"
        )

    except Exception as e:
        output_message = COMMON_ACTION_ERROR_MESSAGE.format(PING_SCRIPT_NAME, e)
        connectivity_result = RESULT_VALUE_FALSE
        status = EXECUTION_STATE_FAILED
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"result_value: {connectivity_result}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.end(output_message, connectivity_result, status)


if __name__ == "__main__":
    main()
