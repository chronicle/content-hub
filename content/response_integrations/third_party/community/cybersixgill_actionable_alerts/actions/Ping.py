from __future__ import annotations

from soar_sdk.ScriptResult import EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

from ..core.AlertsManager import PROVIDER, SixgillEnrichManager


@output_handler
def main():
    try:
        siemplify = SiemplifyAction()
        siemplify.LOGGER.info("----------------- Main - Param Init -----------------")
        client_id = siemplify.extract_configuration_param(PROVIDER, "Client Id")
        client_secret = siemplify.extract_configuration_param(PROVIDER, "Client Secret")
        siemplify.LOGGER.info("----------------- Main - Started -----------------")
        sixgill_manager = SixgillEnrichManager(client_id, client_secret)
        status, message, result = sixgill_manager.create_sixgill_client()
    except Exception as e:
        message = f"Failed to connect to Cybersixgill... Error is {e}"
        siemplify.LOGGER.error(message)
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        result = False
    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  result_value: {result}\n  output_message: {message}",
    )
    siemplify.end(message, result, status)


if __name__ == "__main__":
    main()
