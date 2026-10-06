from __future__ import annotations
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED

from ..core.constants import DEFAULT_FLARE_API_URL, INTEGRATION_NAME, PING_SCRIPT_NAME
from ..core.FlareManager import FlareManager
from ..core.utils import format_user_facing_error, parse_tenant_id


@output_handler
def main():
    """Connectivity test for the Flare API."""
    siemplify = SiemplifyAction()
    siemplify.script_name = PING_SCRIPT_NAME
    siemplify.LOGGER.info("=============== Main - Param Init ===============")

    flare_api_key = siemplify.extract_configuration_param(
        INTEGRATION_NAME, "Flare API Key"
    )
    flare_tenant_id = siemplify.extract_configuration_param(
        INTEGRATION_NAME, "Flare Tenant ID"
    )

    if not flare_api_key:
        siemplify.end(
            "Flare API Key is required. Enter your API key and try again.",
            False,
            EXECUTION_STATE_FAILED,
        )
        return

    siemplify.LOGGER.info("=============== Main - Started ===============")
    status = EXECUTION_STATE_COMPLETED
    result_value = True

    try:
        tenant_id = parse_tenant_id(flare_tenant_id)
        flare = FlareManager(
            api_key=flare_api_key,
            tenant_id=tenant_id,
            api_url=DEFAULT_FLARE_API_URL,
            logger_instance=siemplify.LOGGER,
        )
        flare.test_connection()
        output_message = (
            f"Successfully connected to the {INTEGRATION_NAME} server "
            "with the provided connection parameters!"
        )
    except Exception as error:
        result_value = False
        status = EXECUTION_STATE_FAILED
        friendly = format_user_facing_error(error)
        output_message = (
            f"Failed to connect to the {INTEGRATION_NAME} server! Error: {friendly}"
        )
        siemplify.LOGGER.error(output_message)

    siemplify.LOGGER.info("=============== Main - Finished ===============")
    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"Result Value: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
