from __future__ import annotations

from soar_sdk.ScriptResult import EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

from ..core.VanillaManager import VanillaManager

# Consts:
INTEGRATION_NAME = "VanillaForums"
SCRIPT_NAME = "Ping"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = SCRIPT_NAME
    siemplify.LOGGER.info("================= Main - Param Init =================")

    # Extract intgration params:
    conf = siemplify.get_configuration(INTEGRATION_NAME)
    apiToken = conf.get("API Token")
    baseUrl = conf.get("URL")

    # Create manager for methods:
    vanilla_manager = VanillaManager(apiToken, baseUrl)
    # Init result values:
    status = EXECUTION_STATE_FAILED
    output_message = "The connection failed."
    return_value = False

    try:
        response = vanilla_manager.test_connectivity()
        return_value = True
        output_message = f"Connected successfully to <{baseUrl}>"

    except Exception as e:
        siemplify.LOGGER.error(e)
        output_message += " Error: " + str(e)

    finally:
        siemplify.LOGGER.info("----------------- Main - Finished -----------------")
        siemplify.LOGGER.info(
            f"status: {status}\nresult_value: {return_value}\noutput_message: {output_message}",
        )
        siemplify.end(output_message, return_value, status)


if __name__ == "__main__":
    main()
