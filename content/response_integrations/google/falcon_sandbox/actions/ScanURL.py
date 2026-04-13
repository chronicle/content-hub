# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import annotations
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyUtils import output_handler, convert_dict_to_json_result_dict
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.ScriptResult import (
    EXECUTION_STATE_COMPLETED,
    EXECUTION_STATE_INPROGRESS,
    EXECUTION_STATE_FAILED,
)
from ..core.FalconSandboxManager import FalconSandboxManager
import sys
import base64
import json
from TIPCommon.extraction import extract_configuration_param, extract_action_param

SCRIPT_NAME = "FalconSandbox - Scan URL"
IDENTIFIER = "FalconSandbox"
SUPPORTED_ENTITIES = [EntityTypes.URL, EntityTypes.HOSTNAME]


def get_entity_by_identifier(target_entities, entity_identifier):
    for entity in target_entities:
        if entity.identifier == entity_identifier:
            return entity

    raise Exception(f"Entity with identifier {entity_identifier} was not found.")


@output_handler
def main(is_first_run):
    siemplify = SiemplifyAction()
    siemplify.script_name = SCRIPT_NAME

    mode = "Main" if is_first_run else "QueryState"

    siemplify.LOGGER.info(f"----------------- {mode} - Param Init -----------------")

    # INIT INTEGRATION CONFIGURATION:
    server_address = extract_configuration_param(
        siemplify, provider_name=IDENTIFIER, param_name="Api Root"
    )
    key = extract_configuration_param(
        siemplify, provider_name=IDENTIFIER, param_name="Api Key"
    )

    #  INIT ACTION PARAMETERS:
    threshold = extract_action_param(
        siemplify, param_name="Threshold", input_type=int, print_value=True
    )
    environment_name = extract_action_param(
        siemplify,
        param_name="Environment",
        input_type=str,
        print_value=True,
        default_value="Linux (Ubuntu 16.04, 64 bit)",
    )
    env_id = FalconSandboxManager.get_environment_id_by_name(environment_name)
    siemplify.LOGGER.info(f"Environment ID: {env_id}")
    siemplify.LOGGER.info(f"----------------- {mode} - Started -----------------")

    try:
        manager = FalconSandboxManager(server_address, key)

        if is_first_run:
            successful_jobs, failed_entities = first_run(siemplify, manager, env_id)

            if successful_jobs:
                output_message = f"Successfully submitted {len(list(successful_jobs.keys()))} entities. Waiting for analysis"
                result_value = json.dumps(
                    {
                        "in_progress_jobs": successful_jobs,
                        "init_failed_entities": failed_entities,
                    }
                )
                status = EXECUTION_STATE_INPROGRESS

            else:
                output_message = "Failed to submit the following entities for analysis:\n   {}\nPlease check logs for more information.".format(
                    "\n   ".join([entity for entity in failed_entities])
                )
                result_value = "false"
                status = EXECUTION_STATE_FAILED

        else:
            output_message, result_value, status = handle(siemplify, manager, threshold)

    except Exception as e:
        siemplify.LOGGER.error(
            f"General error occurred while running action {SCRIPT_NAME}"
        )
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        result_value = "false"
        output_message = f"An error occurred while running action. Error: {e}"

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}:")
    siemplify.LOGGER.info(f"Result Value: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.end(output_message, result_value, status)


def first_run(siemplify, manager, env_id):
    """
    Initiate the action - submit the URL/HOSTNAME entities to Falcon analysis
    :param siemplify: {SiemplifyAction} The Siemplify context of the action
    :param manager: {FalconSandboxManager} A manager instance
    :param env_id: {int} The env ID to submit the URLs with
    :return: {tuple} (successful_jobs, failed_entities)
    """
    successful_jobs = {}
    failed_entities = []

    for entity in siemplify.target_entities:
        try:
            if entity.entity_type not in SUPPORTED_ENTITIES:
                siemplify.LOGGER.info(
                    f"Entity {entity.identifier} is of unsupported type. Skipping."
                )
                continue

            siemplify.LOGGER.info(f"Submitting {entity.identifier} for analysis.")
            job_id, sha256 = manager.submit_url(entity.identifier, env_id)
            siemplify.LOGGER.info(
                f"Successfully submitted {entity.identifier}. Job ID: {job_id}"
            )
            successful_jobs[job_id] = {
                "entity_identifier": entity.identifier,
                "sha256": sha256,
            }

        except Exception as e:
            failed_entities.append(entity.identifier)
            siemplify.LOGGER.error(f"An error occurred on entity {entity.identifier}")
            siemplify.LOGGER.exception(e)

    return successful_jobs, failed_entities


def handle(siemplify, manager, threshold):
    """
    Handle the async part of the action
    :param siemplify: SiemplifyAction object
    :param manager: FalconSandboxManager object
    :param threshold: Threshold
    :return: {output message, json result, execution state}
    """
    additional_data = json.loads(siemplify.parameters["additional_data"])
    in_progress_jobs = additional_data["in_progress_jobs"]
    init_failed_entities = additional_data["init_failed_entities"]
    completed_jobs = additional_data.get("completed_jobs", {})
    failed_jobs = additional_data.get("failed_jobs", {})
    json_results = {}
    output_message = ""
    result_value = "false"
    all_finished = True

    for job_id, job_info in list(in_progress_jobs.items()):
        entity_identifier = job_info["entity_identifier"]

        try:
            siemplify.LOGGER.info(
                f"Querying status of job {job_id}, entity {entity_identifier}"
            )
            job_state = manager.get_job_state(job_id)

            if job_state["is_job_completed"]:

                if job_state["is_success"]:
                    siemplify.LOGGER.info(f"Job {job_id} has completed successfully.")
                    completed_jobs[job_id] = job_info

                else:
                    siemplify.LOGGER.info(
                        f"Job {job_id} has completed with status: {job_state['response'].get('state')}. Error: {job_state['response'].get('error')}"
                    )
                    failed_jobs[job_id] = job_info

            else:
                siemplify.LOGGER.info(f"Job {job_id} has not completed yet.")
                all_finished = False

        except Exception as e:
            output_message = f"Unable to get status for job {job_id}. Aborting."
            siemplify.LOGGER.error(output_message)
            siemplify.LOGGER.exception(e)

            return output_message, "false", EXECUTION_STATE_FAILED

    if not all_finished:
        in_progress_jobs = {
            job_id: job_info
            for job_id, job_info in list(in_progress_jobs.items())
            if job_id not in completed_jobs and job_id not in failed_jobs
        }
        total_jobs_count = (
            len(list(in_progress_jobs.keys()))
            + len(list(completed_jobs.keys()))
            + len(list(failed_jobs.keys()))
        )

        siemplify.LOGGER.info(
            f"Jobs in progress: {', '.join(list(in_progress_jobs.keys()))}"
        )
        siemplify.LOGGER.info(
            f"Jobs completed: {', '.join(list(completed_jobs.keys()))}"
        )
        siemplify.LOGGER.info(f"Jobs failed: {', '.join(list(failed_jobs.keys()))}")

        output_message = f"{len(list(in_progress_jobs.keys()))} out of {total_jobs_count} jobs are still in progress. Waiting for completion."

        result_value = json.dumps(
            {
                "in_progress_jobs": in_progress_jobs,
                "init_failed_entities": init_failed_entities,
                "completed_jobs": completed_jobs,
                "failed_jobs": failed_jobs,
            }
        )

        return output_message, result_value, EXECUTION_STATE_INPROGRESS

    if not completed_jobs:
        siemplify.LOGGER.info("All jobs have failed.")
        output_message = "Failed to scan the following entities:\n   {}\n\n".format(
            "\n   ".join(
                [
                    job_info["entity_identifier"]
                    for job_info in list(failed_jobs.values())
                ]
            )
        )
        return output_message, "false", EXECUTION_STATE_FAILED

    siemplify.LOGGER.info(
        f"All jobs have completed ({len(list(completed_jobs.keys()))} successful, {len(list(failed_jobs.keys()))} failed). Fetching reports."
    )
    reports = manager.get_scan_info_by_job_id(list(completed_jobs.keys()))

    successful_entities = []
    no_misp_report_entities = []
    failed_entities = []

    for report in reports:
        job_id = report["job_id"]
        entity_identifier = completed_jobs[job_id]["entity_identifier"]

        try:
            entity = get_entity_by_identifier(
                siemplify.target_entities, entity_identifier
            )
            json_results[entity_identifier] = report
            siemplify.LOGGER.info(
                f"Fetched report for job {job_id}, entity: {entity_identifier}."
            )

            av_detection_rate = report.get("av_detect") or 0
            if int(av_detection_rate) >= threshold:
                siemplify.LOGGER.info(
                    "Marking entity as suspicious and adding an insight."
                )
                entity.is_suspicious = True
                entity.is_enriched = True
                insight_msg = f"Falcon Sandbox - Entity was marked as malicious by av detection score {report.get('av_detect', 0)}. Threshold set to {threshold}"
                siemplify.add_entity_insight(
                    entity, insight_msg, triggered_by=IDENTIFIER
                )

            siemplify.LOGGER.info(
                f"Fetching MISP report for job {job_id}, entity: {entity_identifier}."
            )

            try:
                mist_report_name, misp_report = manager.get_report_by_job_id(
                    job_id, type="misp"
                )
                siemplify.LOGGER.info(
                    f"Fetched MISP report for job {job_id}, entity: {entity_identifier}."
                )

                try:
                    siemplify.result.add_entity_attachment(
                        f"Falcon Sandbox Misp Report - {entity_identifier} - Job {job_id}",
                        mist_report_name,
                        base64.b64encode(misp_report.encode("utf-8")),
                    )
                    successful_entities.append(entity)

                except EnvironmentError as e:
                    siemplify.LOGGER.error(e)
                    siemplify.LOGGER.error(
                        f"MISP report won't be attached for job {job_id}, entity: {entity_identifier}"
                    )
                    no_misp_report_entities.append(entity)
            except Exception as e:
                no_misp_report_entities.append(entity)
                siemplify.LOGGER.error(
                    f"Unable to fetch MISP report for job {job_id}, entity: {entity_identifier}"
                )
                siemplify.LOGGER.exception(e)

        except Exception as e:
            failed_entities.append(entity_identifier)
            siemplify.LOGGER.error(f"An error occurred on entity {entity_identifier}")
            siemplify.LOGGER.exception(e)

    if successful_entities:
        output_message = (
            "Successfully fetched report the following entities:\n   {}\n\n".format(
                "\n   ".join([entity.identifier for entity in successful_entities])
            )
        )
        result_value = "true"
        siemplify.update_entities(successful_entities)

    if no_misp_report_entities:
        output_message += "Fetched scan report but failed to get MISP report for the following entities:\n   {}\n\n".format(
            "\n   ".join([entity.identifier for entity in no_misp_report_entities])
        )
        result_value = "true"
        siemplify.update_entities(no_misp_report_entities)

    if failed_entities:
        output_message += (
            "Failed to fetch reports for the following entities:\n   {}\n\n".format(
                "\n   ".join([entity for entity in failed_entities])
            )
        )

    if failed_jobs:
        output_message += "Failed to scan the following entities:\n   {}\n\n".format(
            "\n   ".join(
                [
                    job_info["entity_identifier"]
                    for job_info in list(failed_jobs.values())
                ]
            )
        )

    if init_failed_entities:
        output_message += "Failed to submit the following entities for analysis:\n   {}\nPlease check logs for more information.".format(
            "\n   ".join([entity for entity in failed_entities])
        )

    siemplify.result.add_result_json(convert_dict_to_json_result_dict(json_results))
    return output_message, result_value, EXECUTION_STATE_COMPLETED


if __name__ == "__main__":
    is_first_run = len(sys.argv) < 3 or sys.argv[2] == "True"
    main(is_first_run)
