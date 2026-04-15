from __future__ import annotations

from soar_sdk.ScriptResult import (
    EXECUTION_STATE_COMPLETED,
    EXECUTION_STATE_FAILED,
    EXECUTION_STATE_INPROGRESS,
)
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

from ..core.api_manager import APIManager
from ..core.censys_exceptions import CensysException
from ..core.constants import (
    COMMON_ACTION_ERROR_MESSAGE,
    GET_RELATED_INFRA_JOB_STATUS_SCRIPT_NAME,
    JOB_ID_REQUIRED_ERROR,
    JOB_STATE_COMPLETED,
    JOB_STATE_FAILED,
    RESULT_VALUE_FALSE,
    RESULT_VALUE_TRUE,
)
from ..core.utils import get_integration_params


@output_handler
def main():
    """Get the current status of a CensEye job asynchronously.

    This action retrieves the current status of a CensEye job by its ID. It supports
    async execution and will return IN_PROGRESS status if the job is still running,
    allowing playbooks to poll until completion.

    Returns:
        None. Results are returned via siemplify.end() with:
            - output_message (str): Status message describing the job state
            - result_value (bool): True if successful, False otherwise
            - status (str): Execution state (COMPLETED, INPROGRESS, or FAILED)

    Raises:
        ValueError: If Job ID validation fails
        CensysException: If API call fails
    """
    siemplify = SiemplifyAction()
    siemplify.script_name = GET_RELATED_INFRA_JOB_STATUS_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    api_key, organization_id, verify_ssl = get_integration_params(siemplify)

    job_id = siemplify.extract_action_param(
        param_name="Job ID", input_type=str, is_mandatory=True
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    status = EXECUTION_STATE_COMPLETED
    result_value = RESULT_VALUE_TRUE
    output_message = ""

    try:
        if not job_id or not job_id.strip():
            raise ValueError(JOB_ID_REQUIRED_ERROR)

        job_id = job_id.strip()

        censys_manager = APIManager(
            api_key,
            organization_id,
            verify_ssl=verify_ssl,
            siemplify=siemplify,
        )

        siemplify.LOGGER.info(f"Retrieving status for CensEye job: {job_id}")
        response = censys_manager.get_censeye_job_status(job_id)

        siemplify.result.add_result_json(response)

        result = response.get("result", {})
        job_state = result.get("state")
        result_count = result.get("result_count", 0)
        create_time = result.get("create_time")
        complete_time = result.get("complete_time")

        if job_state == JOB_STATE_COMPLETED:
            status = EXECUTION_STATE_COMPLETED
            output_message = f"CensEye job {job_id} completed successfully with" \
                f" {result_count} result(s)."
            if complete_time:
                output_message += f" Completed: {complete_time}"
            siemplify.LOGGER.info(
                f"Setting status to EXECUTION_STATE_COMPLETED ({EXECUTION_STATE_COMPLETED})"
            )
            siemplify.LOGGER.info(output_message)

        elif job_state == JOB_STATE_FAILED:
            status = EXECUTION_STATE_FAILED
            result_value = RESULT_VALUE_FALSE
            output_message = f"CensEye job {job_id} failed."
            siemplify.LOGGER.error(
                f"Setting status to EXECUTION_STATE_FAILED ({EXECUTION_STATE_FAILED})"
            )
            siemplify.LOGGER.error(output_message)

        else:
            status = EXECUTION_STATE_INPROGRESS
            output_message = (
                f"CensEye job {job_id} is still in progress (state: {job_state})."
            )
            if create_time:
                output_message += f" Created: {create_time}"
            siemplify.LOGGER.info(
                f"Setting status to EXECUTION_STATE_INPROGRESS ({EXECUTION_STATE_INPROGRESS})"
            )
            siemplify.LOGGER.info(output_message)

    except ValueError as e:
        output_message = str(e)
        result_value = RESULT_VALUE_FALSE
        status = EXECUTION_STATE_FAILED
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)

    except (CensysException, Exception) as e:
        output_message = COMMON_ACTION_ERROR_MESSAGE.format(
            GET_RELATED_INFRA_JOB_STATUS_SCRIPT_NAME, str(e)
        )
        result_value = RESULT_VALUE_FALSE
        status = EXECUTION_STATE_FAILED
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"Result Value: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")

    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
