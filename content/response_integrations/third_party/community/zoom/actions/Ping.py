from __future__ import annotations

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

from ..core.parameters import Parameters
from ..core.ZoomManager import ZoomManager

INTEGRATION_NAME = "Zoom"
SCRIPT_NAME = "Ping"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = SCRIPT_NAME

    siemplify.LOGGER.info("------------------ Main Started -------------------")

    conf = siemplify.get_configuration(INTEGRATION_NAME)
    parameters = Parameters.from_conf(conf)

    try:
        zoom_manager = ZoomManager(**parameters.as_dict(), logger=siemplify.LOGGER)

        zoom_manager.test_connectivity()  # Raises exception if the connect wasn't established

        result_value = True
        output_message = "Connected successfully"

        siemplify.LOGGER.info(
            "Script execution completed: \n"
            f"    Output message: {output_message} \n"
            f"    Result value: {result_value} \n",
        )
        status = EXECUTION_STATE_COMPLETED

    except Exception as e:
        status = EXECUTION_STATE_FAILED
        result_value = False
        output_message = f"Couldn't connect: {e}"

    finally:
        siemplify.end(output_message, result_value, status)

        if status is EXECUTION_STATE_FAILED:
            siemplify.LOGGER.error("Error trying to create a meeting")
            siemplify.LOGGER.exception(output_message)
            raise


if __name__ == "__main__":
    main()
