from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.ScriptResult import (
    EXECUTION_STATE_COMPLETED,
    EXECUTION_STATE_INPROGRESS,
    EXECUTION_STATE_FAILED,
)
from ..core.FalconSandboxManager import (
    FalconSandboxManager,
    COMPLETED_STATUS,
    IN_QUEUE_STATUS,
    IN_PROGRESS_STATUS,
)
from TIPCommon import extract_configuration_param, extract_action_param
import base64


SCRIPT_NAME = "Wait For Job and Fetch Report"
INTEGRATION_NAME = "FalconSandbox"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = f"{INTEGRATION_NAME} - {SCRIPT_NAME}"
    siemplify.LOGGER.info("================= Main - Param Init =================")

    # INIT INTEGRATION CONFIGURATION:
    server_address = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Api Root",
        is_mandatory=True,
        input_type=str,
    )
    key = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Api Key",
        is_mandatory=True,
        input_type=str,
    )

    #  INIT ACTION PARAMETERS:
    job_ids = extract_action_param(
        siemplify, param_name="Job ID", print_value=True, is_mandatory=True
    )
    job_ids = [job_id.strip() for job_id in job_ids.split(",")]

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    completed_jobs = []
    related_jobs = []
    failed_related_jobs = []
    json_results = {}
    failed_jobs = []
    successful_jobs = []
    no_misp_report_jobs = []
    status = EXECUTION_STATE_COMPLETED
    result_value = "false"
    all_finished = True
    output_message = ""

    try:
        manager = FalconSandboxManager(server_address, key)

        for job_id in job_ids:
            try:
                siemplify.LOGGER.info(f"Querying status of job {job_id}")
                job_state = manager.get_job_state(job_id)

                if job_state["response"].get("related_reports", []):
                    siemplify.LOGGER.info(
                        f"Found {len(job_state['response'].get('related_reports', []))} related jobs for job with id {job_id}"
                    )
                    related_jobs.extend(
                        job_state["response"].get("related_reports", [])
                    )

                if job_state["is_job_completed"]:

                    if job_state["is_success"]:
                        siemplify.LOGGER.info(
                            f"Job {job_id} has completed successfully."
                        )
                        completed_jobs.append(job_id)

                    else:
                        siemplify.LOGGER.info(
                            f"Job {job_id} has completed with status: {job_state['response'].get('state')}. Error: {job_state['response'].get('error')}"
                        )
                        failed_jobs.append(job_id)

                else:
                    siemplify.LOGGER.info(f"Job {job_id} has not completed yet.")
                    all_finished = False
                    break

            except Exception as e:
                output_message = f"Unable to get status for job {job_id}."
                siemplify.LOGGER.error(output_message)
                siemplify.LOGGER.exception(e)

                status = EXECUTION_STATE_FAILED
                result_value = "false"

                siemplify.LOGGER.info(
                    "----------------- Main - Finished -----------------"
                )
                siemplify.LOGGER.info(f"Status: {status}:")
                siemplify.LOGGER.info(f"Result Value: {result_value}")
                siemplify.LOGGER.info(f"Output Message: {output_message}")
                siemplify.end(output_message, result_value, status)

        for job in related_jobs:
            job_id = job.get("report_id", "")
            siemplify.LOGGER.info(f"Processing related job with id: {job_id}")
            job_status = job.get("state", "")
            if job_status not in [IN_QUEUE_STATUS, IN_PROGRESS_STATUS]:
                if job_status == COMPLETED_STATUS:
                    siemplify.LOGGER.info(f"Job {job_id} has completed successfully.")
                    completed_jobs.append(job_id)
                else:
                    siemplify.LOGGER.info(
                        f"Job {job_id} has completed with status: {job_status}. Error: {job.get('error', '')}"
                    )
                    failed_related_jobs.append(job)
            else:
                siemplify.LOGGER.info(f"Job {job_id} has not completed yet.")
                all_finished = False
                break

        if related_jobs and len(related_jobs) == len(failed_related_jobs):
            output_message = 'Error executing action "{}". Reason:\n{}'.format(
                SCRIPT_NAME,
                "\n".join([job.get("error", "") for job in failed_related_jobs]),
            )
            status = EXECUTION_STATE_FAILED
            result_value = "false"

            siemplify.LOGGER.info("----------------- Main - Finished -----------------")
            siemplify.LOGGER.info(f"Status: {status}:")
            siemplify.LOGGER.info(f"Result Value: {result_value}")
            siemplify.LOGGER.info(f"Output Message: {output_message}")
            siemplify.end(output_message, result_value, status)

        if not all_finished:
            output_message = "Jobs are in progress. Waiting for completion."
            status = EXECUTION_STATE_INPROGRESS
            result_value = "false"

            siemplify.LOGGER.info("----------------- Main - Finished -----------------")
            siemplify.LOGGER.info(f"Status: {status}:")
            siemplify.LOGGER.info(f"Result Value: {result_value}")
            siemplify.LOGGER.info(f"Output Message: {output_message}")
            siemplify.end(output_message, result_value, status)

        if not completed_jobs:
            siemplify.LOGGER.info("All jobs have failed.")
            output_message = "All jobs have failed."
            status = EXECUTION_STATE_FAILED
            result_value = "false"

            siemplify.LOGGER.info("----------------- Main - Finished -----------------")
            siemplify.LOGGER.info(f"Status: {status}:")
            siemplify.LOGGER.info(f"Result Value: {result_value}")
            siemplify.LOGGER.info(f"Output Message: {output_message}")
            siemplify.end(output_message, result_value, status)

        siemplify.LOGGER.info(
            f"All jobs have completed ({len(completed_jobs)} successful, {(len(failed_jobs) + len(failed_related_jobs))} failed). Fetching reports."
        )
        reports = manager.get_scan_info_by_job_id(completed_jobs)

        for report in reports:
            job_id = report["job_id"]
            json_results[job_id] = report
            siemplify.LOGGER.info(f"Fetched report for job {job_id}.")
            siemplify.LOGGER.info(f"Fetching MISP report for job {job_id}")

            try:
                mist_report_name, misp_report = manager.get_report_by_job_id(
                    job_id, type="misp"
                )
                siemplify.LOGGER.info(f"Fetched MISP report for job {job_id}.")

                try:
                    siemplify.result.add_attachment(
                        f"Falcon Sandbox Misp Report - Job {job_id}",
                        mist_report_name,
                        base64.b64encode(misp_report.encode("utf-8")),
                    )
                    successful_jobs.append(job_id)

                except EnvironmentError as e:
                    siemplify.LOGGER.error(e)
                    siemplify.LOGGER.error(
                        f"MISP report won't be attached for job {job_id}"
                    )
                    no_misp_report_jobs.append(job_id)

            except Exception as e:
                no_misp_report_jobs.append(job_id)
                siemplify.LOGGER.error(f"Unable to fetch MISP report for job {job_id}")
                siemplify.LOGGER.exception(e)

        if successful_jobs:
            output_message = (
                "Successfully fetched report for the following jobs:\n{}\n\n".format(
                    "\n   ".join([job_id for job_id in successful_jobs])
                )
            )
            result_value = "true"

        if no_misp_report_jobs:
            output_message += "Fetched scan report but failed to get MISP report for the following jobs:\n{}\n\n".format(
                "\n   ".join([job_id for job_id in no_misp_report_jobs])
            )

        if failed_jobs:
            output_message += (
                "Failed to fetch report for the following jobs:\n{}\n\n".format(
                    "\n   ".join([job_id for job_id in failed_jobs])
                )
            )

        if failed_related_jobs:
            output_message += (
                "Some of the related reports were not available. Here are the related "
                "errors:\n{}\n".format(
                    "\n".join([job.get("error", "") for job in failed_related_jobs])
                )
            )

    except Exception as e:
        siemplify.LOGGER.error(
            f"General error occurred while running action {SCRIPT_NAME}"
        )
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        result_value = "false"
        output_message = f"An error occurred while running action. Error: {e}"

    siemplify.result.add_result_json(json_results)
    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}:")
    siemplify.LOGGER.info(f"Result Value: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
