from __future__ import annotations
import base64
import copy
import json
import sys

import arrow
from TIPCommon import extract_configuration_param, extract_action_param

from ..core.CiscoThreatGridManager import CiscoThreatGridManager
from soar_sdk.ScriptResult import (
    EXECUTION_STATE_COMPLETED,
    EXECUTION_STATE_FAILED,
    EXECUTION_STATE_INPROGRESS,
)
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyUtils import construct_csv, convert_dict_to_json_result_dict
from soar_sdk.SiemplifyUtils import output_handler
from ..core.consts import (
    INTEGRATION_NAME,
    GET_SUBMISSIONS_SCRIPT_NAME,
    ENTITY_TERM_MAPPER,
    NO_RESULTS,
    TO_PROCESS,
    WAITING_STATE,
    FAILED,
    DEFAULT_THREAT_SCORE_THRESHOLD,
    DEFAULT_MAX_RESULTS,
    MAX_LIMIT_VALUE,
    MIN_LIMIT_VALUE,
)


def start_operation(siemplify, cisco_threat_grid, threshold, max_to_return):
    """
    This method will run only in the first run of the action and will make requests from Cisco for submissions from
    Cisco ThreatGrid
    :param siemplify: Siemplify object
    :param cisco_threat_grid: {CiscoThreatGridManager} Cisco ThreatGrid manager to communicate with ThreatGrid service
    :param threshold: {int} Above this parameter, the entity will be marked as suspicious
    :param max_to_return: {int} Max results to return
    return: (output_message, result_value, status)
    """
    status = EXECUTION_STATE_INPROGRESS
    output_message = ""

    no_results_entities = []
    in_progress_entities = []
    to_process_entities = []
    failed_entities = []

    for entity in siemplify.target_entities:
        siemplify.LOGGER.info(
            f"Start processing entity with identifier: {entity.identifier}"
        )
        submission_state = ""
        try:
            if (
                entity.entity_type == EntityTypes.ADDRESS
                or entity.entity_type == EntityTypes.FILEHASH
            ):
                submission_state = cisco_threat_grid.get_submission_state(
                    entity.identifier, limit=max_to_return
                )
            elif entity.entity_type in list(ENTITY_TERM_MAPPER.keys()):
                submission_state = cisco_threat_grid.get_submission_state(
                    entity.identifier,
                    ENTITY_TERM_MAPPER.get(entity.entity_type),
                    limit=max_to_return,
                )

            siemplify.LOGGER.info(
                f"Submission state of identifier is: {submission_state}"
            )
            if submission_state == TO_PROCESS:
                to_process_entities.append(entity.identifier)
            elif submission_state == WAITING_STATE:
                in_progress_entities.append(entity.identifier)
            elif submission_state == NO_RESULTS:
                no_results_entities.append(entity.identifier)

        except Exception as e:
            failed_entities.append(entity.identifier)
            # An error occurred - skip entity and continue
            siemplify.LOGGER.error(
                f"An error occurred on entity: {entity.identifier}.\n{str(e)}."
            )
            siemplify.LOGGER.exception(e)

    submissions_status = {
        TO_PROCESS: to_process_entities,
        WAITING_STATE: in_progress_entities,
        NO_RESULTS: no_results_entities,
        FAILED: failed_entities,
    }

    if in_progress_entities:
        output_message += "Waiting for all submissions to be processed..."
        result_value = json.dumps(submissions_status)

    else:
        output_message, result_value, status = finish_operation(
            siemplify=siemplify,
            cisco_threat_grid=cisco_threat_grid,
            submissions_status=submissions_status,
            threshold=threshold,
            max_to_return=max_to_return,
        )

    return output_message, result_value, status


def query_operation_status(
    siemplify, cisco_threat_grid, threshold, submissions_status_dict, max_to_return
):
    """
    This method will run from the second time the action is run and will make requests from Cisco for submissions from
    Cisco ThreatGrid
    :param siemplify: Siemplify object
    :param cisco_threat_grid: {CiscoThreatGridManager} Cisco ThreatGrid manager to communicate with ThreatGrid service
    :param threshold: {int} Above this parameter, the entity will be marked as suspicious
    :param submissions_status_dict: {Dict} The status of the requests from Cisco ThreatGrid (wait/to_process)
    :param max_to_return: {int} Max results to return
    :return: (output_message, result_value, status)
    """
    copy_waiting_list = copy.deepcopy(submissions_status_dict[WAITING_STATE])
    for entity in siemplify.target_entities:
        if entity.identifier in submissions_status_dict[WAITING_STATE]:
            submission_state = ""
            try:
                siemplify.LOGGER.info(
                    f"Continue processing entity with identifier: {entity.identifier}"
                )
                if (
                    entity.entity_type == EntityTypes.ADDRESS
                    or entity.entity_type == EntityTypes.FILEHASH
                ):
                    submission_state = cisco_threat_grid.get_submission_state(
                        entity.identifier, limit=max_to_return
                    )
                elif entity.entity_type in list(ENTITY_TERM_MAPPER.keys()):
                    submission_state = cisco_threat_grid.get_submission_state(
                        entity.identifier,
                        ENTITY_TERM_MAPPER.get(entity.entity_type),
                        limit=max_to_return,
                    )

                if submission_state == TO_PROCESS:
                    copy_waiting_list.remove(entity.identifier)
                    submissions_status_dict[TO_PROCESS].append(entity.identifier)

            except Exception as e:
                submissions_status_dict[FAILED].append(entity.identifier)
                # An error occurred - skip entity and continue
                siemplify.LOGGER.error(
                    f"An error occurred on entity: {entity.identifier}.\n{str(e)}."
                )
                siemplify.LOGGER.exception(e)

    submissions_status_dict[WAITING_STATE] = copy_waiting_list

    if submissions_status_dict[WAITING_STATE]:
        output_message = "Waiting for all submissions to be processed..."
        result_value = json.dumps(submissions_status_dict)
        status = EXECUTION_STATE_INPROGRESS

    else:
        output_message, result_value, status = finish_operation(
            siemplify=siemplify,
            cisco_threat_grid=cisco_threat_grid,
            submissions_status=submissions_status_dict,
            threshold=threshold,
            max_to_return=max_to_return,
        )
    return output_message, result_value, status


def finish_operation(
    siemplify, cisco_threat_grid, submissions_status, threshold, max_to_return
):
    """
    Once all entities have been returned and there are no more entities in wait mode,process the returned data from
    Cisco ThreatGrid
    :param siemplify: Siemplify object
    :param cisco_threat_grid: {CiscoThreatGridManager} Cisco ThreatGrid manager to communicate with ThreatGrid service
    :param submissions_status: {Dict} The status of the requests from Cisco ThreatGrid (wait/to_process)
    :param threshold: {int} Above this parameter, the entity will be marked as suspicious
    :return: (output_message, result_value, status)
    :param max_to_return: {int} Max results to return
    """
    enriched_entities = []
    json_results = {}

    for entity in siemplify.target_entities:
        if entity.identifier in submissions_status[TO_PROCESS]:
            try:
                siemplify.LOGGER.info(
                    f"Finalizing submission with identifier: {entity.identifier}"
                )
                submissions = []
                if (
                    entity.entity_type == EntityTypes.ADDRESS
                    or entity.entity_type == EntityTypes.FILEHASH
                ):
                    submissions = cisco_threat_grid.get_submissions(
                        entity.identifier, limit=max_to_return
                    )
                elif entity.entity_type in list(ENTITY_TERM_MAPPER.keys()):
                    submissions = cisco_threat_grid.get_submissions(
                        entity.identifier,
                        ENTITY_TERM_MAPPER.get(entity.entity_type),
                        limit=max_to_return,
                    )

                if submissions:
                    submissions_table = cisco_threat_grid.create_submissions_table(
                        submissions
                    )
                    json_results[entity.identifier] = submissions_table

                    csv_output = construct_csv(submissions_table)
                    siemplify.result.add_entity_table(
                        f"{entity.identifier} - Submissions", csv_output
                    )

                    submissions = sorted(
                        submissions,
                        key=lambda submission: arrow.get(
                            submission["item"]["submitted_at"]
                        ).timestamp,
                    )
                    most_recent_sample_id = submissions[-1]["item"]["sample"]

                    try:
                        # Download report
                        full_report = cisco_threat_grid.get_sample_report(
                            most_recent_sample_id
                        )
                        siemplify.result.add_entity_attachment(
                            f"{entity.identifier} - Most Recent Analysis Report",
                            f"{most_recent_sample_id}.html",
                            base64.b64encode(full_report.encode("utf-8")),
                        )
                    except Exception as e:
                        # Attachment cannot be larger than 3 MB
                        siemplify.LOGGER.error(
                            f"Can not add html report for {most_recent_sample_id}:\n{str(e)}."
                        )

                    try:
                        # Download pcap
                        pcap = cisco_threat_grid.get_sample_pcap(most_recent_sample_id)
                        siemplify.result.add_entity_attachment(
                            f"{entity.identifier} - Most Recent Network Pcap",
                            f"{most_recent_sample_id}.pcap",
                            base64.b64encode(pcap.encode("utf-8")),
                        )
                    except Exception as e:
                        # Attachment cannot be larger than 3 MB
                        siemplify.LOGGER.error(
                            f"Can not add pcap for {most_recent_sample_id}:\n{str(e)}."
                        )

                    try:
                        # Download screenshot
                        screenshot = cisco_threat_grid.get_sample_screenshot(
                            most_recent_sample_id
                        )
                        siemplify.result.add_entity_attachment(
                            f"{entity.identifier} - Most Recent Screenshot",
                            f"{most_recent_sample_id}.png",
                            base64.b64encode(screenshot.encode("utf-8")),
                        )
                    except Exception as e:
                        # Attachment cannot be larger than 3 MB
                        siemplify.LOGGER.error(
                            f"Can not add screenshot for {most_recent_sample_id}:\n{str(e)}."
                        )

                    try:
                        threat = cisco_threat_grid.get_sample_threat(
                            most_recent_sample_id
                        )
                        threat_table = cisco_threat_grid.create_threat_table(threat)
                        if threat_table:
                            csv_output = construct_csv(threat_table)
                            siemplify.result.add_entity_table(
                                f"{entity.identifier} - Most Recent Threat Report",
                                csv_output,
                            )
                    except Exception as e:
                        # Attachment cannot be larger than 3 MB
                        siemplify.LOGGER.error(
                            f"Can not add threat table for {most_recent_sample_id}:\n{str(e)}."
                        )

                    max_score = cisco_threat_grid.get_max_threat_score(submissions)
                    entity.additional_properties.update(
                        {"ThreatGrid Max Score": max_score}
                    )

                    entity.is_enriched = True
                    enriched_entities.append(entity)
                    if max_score > threshold:
                        entity.is_suspicious = True

            except Exception as e:
                submissions_status[FAILED].append(entity.identifier)
                # An error occurred - skip entity and continue
                siemplify.LOGGER.error(
                    f"An error occurred on entity: {entity.identifier}.\n{str(e)}."
                )
                siemplify.LOGGER.exception(e)

    if enriched_entities:
        entities_names = [entity.identifier for entity in enriched_entities]
        output_message = (
            "Cisco Threat Grid - Found submissions for the following entities\n"
            + "\n".join(entities_names)
        )

        siemplify.update_entities(enriched_entities)
        siemplify.result.add_result_json(convert_dict_to_json_result_dict(json_results))
        result_value = True
        if submissions_status[FAILED]:
            output_message += (
                "\n\nFailed to get submissions for the following entities\n"
                + "\n".join(submissions_status[FAILED])
            )
        if submissions_status[NO_RESULTS]:
            output_message += (
                "\n\nNo data found for the following entities\n"
                + "\n".join(submissions_status[NO_RESULTS])
            )
    else:
        output_message = "No data found for the current entities.\n"
        result_value = False

    status = EXECUTION_STATE_COMPLETED
    return output_message, result_value, status


@output_handler
def main(is_first_run):
    siemplify = SiemplifyAction()
    siemplify.script_name = GET_SUBMISSIONS_SCRIPT_NAME

    server_addr = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Api Root",
        is_mandatory=True,
        print_value=True,
    )
    api_key = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Api Key",
        is_mandatory=True,
        print_value=False,
    )
    use_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Use SSL",
        is_mandatory=True,
        print_value=True,
        input_type=bool,
        default_value=True,
    )

    mode = "Main" if is_first_run else "Get Submissions"
    siemplify.LOGGER.info(f"----------------- {mode} - Started -----------------")

    try:
        threshold = extract_action_param(
            siemplify,
            param_name="Threshold",
            print_value=True,
            input_type=int,
            is_mandatory=True,
            default_value=DEFAULT_THREAT_SCORE_THRESHOLD,
        )

        max_to_return = extract_action_param(
            siemplify,
            param_name="Max Submissions To Return",
            print_value=True,
            input_type=int,
            is_mandatory=False,
            default_value=DEFAULT_MAX_RESULTS,
        )

        if max_to_return is not None and not (
            MIN_LIMIT_VALUE <= max_to_return <= MAX_LIMIT_VALUE
        ):
            max_to_return = DEFAULT_MAX_RESULTS
            siemplify.LOGGER.info(
                "'Max Submissions To Return' Should be in range of [{}, {}]. A default value ({})"
                " is applied to the parameter".format(
                    MIN_LIMIT_VALUE, MAX_LIMIT_VALUE, DEFAULT_MAX_RESULTS
                )
            )

        cisco_threat_grid = CiscoThreatGridManager(server_addr, api_key, use_ssl)

        if is_first_run:
            cisco_threat_grid.test_connectivity()
            output_message, result_value, status = start_operation(
                siemplify=siemplify,
                cisco_threat_grid=cisco_threat_grid,
                threshold=threshold,
                max_to_return=max_to_return,
            )

        else:
            submissions_status = json.loads(
                siemplify.parameters.get("additional_data", {})
            )
            output_message, result_value, status = query_operation_status(
                siemplify=siemplify,
                cisco_threat_grid=cisco_threat_grid,
                threshold=threshold,
                max_to_return=max_to_return,
                submissions_status_dict=submissions_status,
            )

    except Exception as error:
        result_value = False
        status = EXECUTION_STATE_FAILED
        output_message = f"Error executing action 'Get Submissions'. Reason: {error}"
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(error)

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}:")
    siemplify.LOGGER.info(f"Result Value: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    is_first_run = len(sys.argv) < 3 or sys.argv[2] == "True"
    main(is_first_run)
