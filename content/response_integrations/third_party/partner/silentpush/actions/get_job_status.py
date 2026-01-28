from ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from SiemplifyUtils import output_handler
from soar_sdk.SiemplifyAction import SiemplifyAction

from ..core.constants import GET_JOB_STATUS_SCRIPT_NAME, INTEGRATION_NAME
from ..core.silent_push_manager import SilentPushManager


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = GET_JOB_STATUS_SCRIPT_NAME

    # Extract Integration config
    server_url = siemplify.extract_configuration_param(
        INTEGRATION_NAME, "Silent Push Server"
    )
    api_key = siemplify.extract_configuration_param(INTEGRATION_NAME, "API Key")

    # Extract action parameter
    job_id = siemplify.extract_action_param("job_id", print_value=True)
    max_wait = siemplify.extract_action_param("max_wait", print_value=True)
    status_only = siemplify.extract_action_param("status_only", print_value=True)
    force_metadata_on = siemplify.extract_action_param(
        "force_metadata_on", print_value=True
    )
    force_metadata_off = siemplify.extract_action_param(
        "force_metadata_off", print_value=True
    )

    if max_wait:
        max_wait = int(max_wait)
    params = {
        "max_wait": max_wait or 20,
        "status_only": status_only,
        "force_metadata_on": force_metadata_on,
        "force_metadata_off": force_metadata_off,
    }
    status = EXECUTION_STATE_COMPLETED  # used to flag back to siemplify system, the action final status
    output_message = (
        "output message :"  # human readable message, showed in UI as the action result
    )
    result_value = (
        None  # Set a simple result value, used for playbook if\else and placeholders.
    )

    try:
        sp_manager = SilentPushManager(server_url, api_key, logger=siemplify.LOGGER)
        raw_response = sp_manager.get_job_status(job_id, params)
        job_status = raw_response.get("response", {})

        if not job_status:
            error_message = f"No job status found for Job ID: {job_id}"
            siemplify.LOGGER.error(error_message)
            status = EXECUTION_STATE_FAILED
            siemplify.end(error_message, "false", status)

        output_message = f"{job_status}"
        status = EXECUTION_STATE_COMPLETED
        result_value = True
    except Exception as error:
        result_value = False
        status = EXECUTION_STATE_FAILED
        output_message = (
            f"Failed to retrieve to the job status of job ID :{job_id} "
            f"for {INTEGRATION_NAME} server! Error: {error}"
        )
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(error)

    for entity in siemplify.target_entities:
        print(entity.identifier)

    siemplify.LOGGER.info(
        "\n  status: {}\n  result_value: {}\n  output_message: {}".format(
            status, result_value, output_message
        )
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
