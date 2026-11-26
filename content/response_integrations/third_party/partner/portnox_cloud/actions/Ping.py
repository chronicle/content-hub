from __future__ import annotations

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

from ..core.action_utils import create_manager
from ..core.constants import INTEGRATION_DISPLAY_NAME, INTEGRATION_IDENTIFIER

SCRIPT_NAME = "Ping"


@output_handler
def main() -> None:
    siemplify = SiemplifyAction()
    siemplify.script_name = f"{INTEGRATION_IDENTIFIER} - {SCRIPT_NAME}"
    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    try:
        manager = create_manager(siemplify)
        manager.test_connectivity()
        status = EXECUTION_STATE_COMPLETED
        result_value = True
        output_message = (
            f"Successfully connected to the {INTEGRATION_DISPLAY_NAME} server with the provided connection parameters!"
        )
    except Exception as error:
        siemplify.LOGGER.exception(error)
        status = EXECUTION_STATE_FAILED
        result_value = False
        output_message = f"Failed to connect to the {INTEGRATION_DISPLAY_NAME} server! Error is {error}"

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
