from __future__ import annotations
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import unix_now, convert_unixtime_to_datetime, output_handler
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED,EXECUTION_STATE_TIMEDOUT
from ..core.constants import OAUTH_CONFIG
from ..core.ApiManager import ApiManager
import requests


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.LOGGER.info("----------------- RRS - Volume Offline: Init -----------------")
    rrsManager = ApiManager(siemplify)
    siemplify.LOGGER.info("----------------- RRS - Volume Offline: Started -----------------")

    volume_offline_result = None
    try:
        
        # call volume offline api
        volume_offline_result = rrsManager.volume_offline()

        status = EXECUTION_STATE_COMPLETED  # used to flag back to siemplify system, the action final status
        output_message = "Successfully took volume offline"  # human readable message, showed in UI as the action result
        result_value = True  # Set a simple result value, used for playbook if\else and placeholders.

    except Exception as e:
        output_message = f"Failed to take volume offline. Error: {e}"
        siemplify.LOGGER.error(f"Volume Offline: Failed to take volume offline. Error: {e}")
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED    
        result_value = False

    siemplify.LOGGER.info("----------------- RRS - Volume Offline: End -----------------")
    siemplify.LOGGER.info("\n  status: {}\n  result_value: {}\n  output_message: {}".format(status,result_value, output_message))
    
    # Add result to action output.
    siemplify.result.add_result_json(volume_offline_result)
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
