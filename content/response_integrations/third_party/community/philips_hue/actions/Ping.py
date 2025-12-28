from __future__ import annotations

from soar_sdk.ScriptResult import EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

from ..core.PhilipsManager import PhilipsManager

# Consts:
INTEGRATION_NAME = "PhilipsHUE"
SCRIPT_NAME = "Ping"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = SCRIPT_NAME
    siemplify.LOGGER.info("================= Main - Param Init =================")

    # Extract intgration params:
    bridge_ip = siemplify.extract_configuration_param(INTEGRATION_NAME, "Bridge IP")
    user_name = siemplify.extract_configuration_param(
        INTEGRATION_NAME,
        "Authorized Username",
    )

    # Create manager for methods:
    philips_manager = PhilipsManager(bridge_ip, user_name)
    # Init result values:
    status = EXECUTION_STATE_FAILED
    output_message = "The connection failed."
    return_value = False

    try:
        connection_successful = philips_manager.test_connectivity()
        return_value = connection_successful
        output_message = f"Connected successfully to <{bridge_ip}>"

    except:
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
