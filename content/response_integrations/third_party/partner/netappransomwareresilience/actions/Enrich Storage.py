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
    siemplify.LOGGER.info("----------------- RRS - Enrich Storage: Init -----------------")
    rrsManager = ApiManager(siemplify)
    siemplify.LOGGER.info("----------------- RRS - Enrich Storage: Started -----------------")

    enrich_results = None
    try:
        
        # call enrich storage api
        enrich_results = rrsManager.enrich_storage()

        status = EXECUTION_STATE_COMPLETED  # used to flag back to siemplify system, the action final status
        output_message = "Successfully enriched storage information"  # human readable message, showed in UI as the action result
        result_value = True  # Set a simple result value, used for playbook if\else and placeholders.

    except Exception as e:
        output_message = f"Failed to enrich storage. Error: {e}"
        siemplify.LOGGER.error(f"Enrich Storage: Failed to enrich storage. Error: {e}")
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED    
        result_value = False

    siemplify.LOGGER.info("----------------- RRS - Enrich Storage: End -----------------")
    siemplify.LOGGER.info(f"Enrich Storage output: \n  status: {status}\n  result_value: {result_value}\n  output_message: {output_message}")
    
    # Add result to action output.
    siemplify.result.add_result_json(enrich_results)
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
