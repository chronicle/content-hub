from __future__ import annotations

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

from ..core.api_manager import ApiManager
from ..core.rrs_exceptions import RrsException


@output_handler
def main() -> None:
    """Check the status of a previously triggered RRS job.

    Queries the Ransomware Resilience Service API for the current status of a
    job and reports the result back to the SOAR platform.
    """
    siemplify = SiemplifyAction()
    siemplify.LOGGER.info("----------------- RRS - Check Job Status: Init -----------------")

    job_status_result = {}
    try:
        rrsManager = ApiManager(siemplify)
        # Extract parameters from action
        source = siemplify.extract_action_param("Source", print_value=True)
        agent_id = siemplify.extract_action_param("Agent ID", print_value=True)
        job_id = siemplify.extract_action_param("Job ID", print_value=True)
        siemplify.LOGGER.info("----------------- RRS - Check Job Status: Started -----------------")

        # call check job status api
        job_status_result = rrsManager.check_job_status(source, agent_id, job_id)

        # used to flag back to siemplify system, the action final status
        status = EXECUTION_STATE_COMPLETED
        # human readable message, showed in UI as the action result
        output_message = "Successfully retrieved job status"
        # Set a simple result value, used for playbook if\else and placeholders.
        result_value = True

    except RrsException as e:
        output_message = str(e)
        siemplify.LOGGER.error(f"Check Job Status: RRS error - {e}")
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        result_value = False
        job_status_result = {}

    except Exception as e:
        output_message = f"Failed to check job status. Error: {e}"
        siemplify.LOGGER.error(f"Check Job Status: Failed to check job status. Error: {e}")
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        result_value = False
        job_status_result = {}

    siemplify.LOGGER.info("----------------- RRS - Check Job Status: End -----------------")
    siemplify.LOGGER.info(
        f"Check Job Status output: \n  status: {status}\n  result_value: {result_value}"
        f"\n  output_message: {output_message}"
    )

    # Add result to action output.
    siemplify.result.add_result_json(job_status_result)
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
