from __future__ import annotations
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import unix_now, convert_unixtime_to_datetime, output_handler
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED,EXECUTION_STATE_TIMEDOUT
from ..core.ApiManager import ApiManager
from ..core.rrs_exceptions import RrsException


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.LOGGER.info("----------------- RRS - Take Snapshot: Init -----------------")

    snapshot_result = None
    try:
        rrsManager = ApiManager(siemplify)
        siemplify.LOGGER.info("----------------- RRS - Take Snapshot: Started -----------------")
        
        # call take snapshot api
        snapshot_result = rrsManager.take_snapshot()

        status = EXECUTION_STATE_COMPLETED  # used to flag back to siemplify system, the action final status
        output_message = "Successfully triggered snapshot creation"  # human readable message, showed in UI as the action result
        result_value = True  # Set a simple result value, used for playbook if\else and placeholders.

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
    siemplify.LOGGER.info(f"Take Snapshot: \n  status: {status}\n  result_value: {result_value}\n  output_message: {output_message}")
    
    # Add result to action output.
    siemplify.result.add_result_json(snapshot_result)
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
