from __future__ import annotations

from soar_sdk.ScriptResult import EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

from ..core.WebhookManager import WebhookManager

# Consts:
INTEGRATION_NAME = "Webhook"
SCRIPT_NAME = "Ping"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = SCRIPT_NAME
    siemplify.LOGGER.info("================= Main - Param Init =================")

    # Init integration params:
    conf = siemplify.get_configuration(INTEGRATION_NAME)
    baseUrl = conf.get("URL")

    # Create manager instance for methods:
    webhookManager = WebhookManager(baseUrl)

    # Init result values:
    status = EXECUTION_STATE_FAILED
    output_message = "Failed to connect to the webhook integration."
    return_value = False

    try:
        response = webhookManager.test_connectivity()
        return_value = True
        output_message = "Successfully connected to the webhook integration."
        status = 0 # Assuming 0 is success, or EXECUTION_STATE_COMPLETED if imported

    except Exception as e:
        siemplify.LOGGER.error(e)
        output_message += f" Error: {e}"

    finally:
        siemplify.LOGGER.info("----------------- Main - Finished -----------------")
        siemplify.LOGGER.info(
            f"status: {status}\nresult_value: {return_value}\noutput_message: {output_message}",
        )
        siemplify.end(output_message, return_value, status)


if __name__ == "__main__":
    main()


