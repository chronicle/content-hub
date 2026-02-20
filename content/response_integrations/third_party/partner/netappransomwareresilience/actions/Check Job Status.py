from __future__ import annotations
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import unix_now, convert_unixtime_to_datetime, output_handler
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED,EXECUTION_STATE_TIMEDOUT
from ..core.constants import OAUTH_CONFIG
from ..core.ApiManager import ApiManager


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.LOGGER.info("----------------- RRS - Check Job Status: Init -----------------")
    rrsManager = ApiManager(siemplify)
    siemplify.LOGGER.info("----------------- RRS - Check Job Status: Started -----------------")

    job_status_result = None
    try:
        
        # call check job status api
        job_status_result = rrsManager.check_job_status()

        status = EXECUTION_STATE_COMPLETED  # used to flag back to siemplify system, the action final status
        output_message = "Successfully retrieved job status"  # human readable message, showed in UI as the action result
        result_value = True  # Set a simple result value, used for playbook if\else and placeholders.

    except Exception as e:
        output_message = f"Failed to check job status. Error: {e}"
        siemplify.LOGGER.error(f"Check Job Status: Failed to check job status. Error: {e}")
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED    
        result_value = False

    siemplify.LOGGER.info("----------------- RRS - Check Job Status: End -----------------")
    siemplify.LOGGER.info(f"Check Job Status output: \n  status: {status}\n  result_value: {result_value}\n  output_message: {output_message}")
    
    # Add result to action output.
    siemplify.result.add_result_json(job_status_result)
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
