from __future__ import annotations

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

from ..core.config import create_manager_from_siemplify
from ..core.constants import INTEGRATION_NAME

SCRIPT_NAME = "Ping"


@output_handler
def main() -> None:
    siemplify = SiemplifyAction()
    siemplify.script_name = SCRIPT_NAME

    try:
        doppel_manager = create_manager_from_siemplify(siemplify)
        doppel_manager.connection_test()
        output_message = (
            f"Successfully connected to the {INTEGRATION_NAME} server with the provided "
            "connection parameters!"
        )
        siemplify.end(output_message, True, EXECUTION_STATE_COMPLETED)
    except Exception as e:
        siemplify.end(
            f"Failed to connect to the {INTEGRATION_NAME} server! Error is {e}",
            False,
            EXECUTION_STATE_FAILED,
        )


if __name__ == "__main__":
    main()
