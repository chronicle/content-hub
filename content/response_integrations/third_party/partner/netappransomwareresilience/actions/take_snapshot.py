from __future__ import annotations

from soar_sdk.ScriptResult import (
    EXECUTION_STATE_COMPLETED,
    EXECUTION_STATE_FAILED,
)
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

from ..core.api_manager import ApiManager
from ..core.rrs_exceptions import RrsException


@output_handler
def main() -> None:
    """Trigger a snapshot creation via the Ransomware Resilience Service.

    Calls the RRS API to initiate a new snapshot and reports the result back
    to the SOAR platform.
    """
    siemplify = SiemplifyAction()
    siemplify.LOGGER.info("----------------- RRS - Take Snapshot: Init -----------------")

    snapshot_result = None
    try:
        rrsManager = ApiManager(siemplify)
        # Extract parameters from action
        volume_id = siemplify.extract_action_param("Volume ID", print_value=True)
        agent_id = siemplify.extract_action_param("Agent ID", print_value=True)
        system_id = siemplify.extract_action_param("System ID", print_value=True)
        siemplify.LOGGER.info("----------------- RRS - Take Snapshot: Started -----------------")

        # call take snapshot api
        snapshot_result = rrsManager.take_snapshot(volume_id, agent_id, system_id)

        # used to flag back to siemplify system, the action final status
        status = EXECUTION_STATE_COMPLETED
        # human readable message, showed in UI as the action result
        output_message = "Successfully triggered snapshot creation"
        # Set a simple result value, used for playbook if\else and placeholders.
        result_value = True

    except RrsException as e:
        output_message = str(e)
        siemplify.LOGGER.error(f"Take Snapshot: RRS error - {e}")
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        result_value = False
        snapshot_result = {}

    except Exception as e:
        output_message = f"Failed to take snapshot. Error: {e}"
        siemplify.LOGGER.error(f"Take Snapshot: Failed to take snapshot. Error: {e}")
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        result_value = False
        snapshot_result = {}

    siemplify.LOGGER.info("----------------- RRS - Take Snapshot: End -----------------")
    siemplify.LOGGER.info(
        f"Take Snapshot: \n  status: {status}\n  result_value: {result_value}"
        f"\n  output_message: {output_message}"
    )

    # Add result to action output.
    siemplify.result.add_result_json(snapshot_result)
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
