from __future__ import annotations
import json
import sys

from TIPCommon import extract_configuration_param, extract_action_param, construct_csv

from ..core.LogPointManager import LogPointManager
from soar_sdk.ScriptResult import (
    EXECUTION_STATE_COMPLETED,
    EXECUTION_STATE_FAILED,
    EXECUTION_STATE_INPROGRESS,
    EXECUTION_STATE_TIMEDOUT,
)
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler, unix_now
from ..core.consts import (
    INTEGRATION_NAME,
    EXECUTE_QUERY,
    CUSTOM_QUERY_TIME_FRAME,
    DEFAULT_MAX_REPOS,
    DEFAULT_TIME_FRAME,
    SEARCH_ID,
    RESULTS,
    TIME_FRAME_MAPPING,
    MIN_REPOS,
)
from ..core.exceptions import LogPointInvalidParametersException
from ..core.utils import load_csv_to_list, get_time_frame


def start_operation(siemplify, manager):
    query = extract_action_param(
        siemplify,
        param_name="Query",
        is_mandatory=True,
        print_value=True,
        default_value="",
        input_type=str,
    )

    time_frame = extract_action_param(
        siemplify,
        param_name="Time Frame",
        is_mandatory=True,
        print_value=True,
        default_value=DEFAULT_TIME_FRAME,
    )

    start_time = extract_action_param(
        siemplify, param_name="Start Time", is_mandatory=False, print_value=True
    )

    end_time = extract_action_param(
        siemplify, param_name="End Time", is_mandatory=False, print_value=True
    )

    repos = extract_action_param(
        siemplify, param_name="Repos", is_mandatory=False, print_value=True
    )

    limit = extract_action_param(
        siemplify,
        param_name="Max Results To Return",
        is_mandatory=False,
        print_value=True,
        input_type=int,
        default_value=DEFAULT_MAX_REPOS,
    )

    if limit < MIN_REPOS:
        raise LogPointInvalidParametersException(
            f"'Max Repos To Return' must be an integer greater or equals "
            f"to '{MIN_REPOS}'"
        )

    repos = load_csv_to_list(repos, "Repos") if repos else []

    siemplify.LOGGER.info("Start handling time frame")
    if time_frame == CUSTOM_QUERY_TIME_FRAME:
        siemplify.LOGGER.info(f"{CUSTOM_QUERY_TIME_FRAME} time frame selected")
        if not start_time:
            siemplify.LOGGER.info(
                "you need to provide"
                " “Start Time”, if “Custom” is selected for time frame."
            )
            raise LogPointInvalidParametersException(
                "you need to provide “Start Time”, if “Custom” is selected for time "
                "frame."
            )

        #  Format time_frame
        time_range = get_time_frame(start_time, end_time)

    # time_frame is one of the possible configured values
    else:
        time_range = TIME_FRAME_MAPPING[time_frame]

    siemplify.LOGGER.info(f"Done handling time frame. \nTime Frame: {time_range}")

    status = EXECUTION_STATE_INPROGRESS
    output_message = ""

    # if repos list is not empty
    repos_addresses = []
    if repos:
        siemplify.LOGGER.info(f"Fetching repos from {INTEGRATION_NAME}")
        repos_objects = manager.list_repos()
        siemplify.LOGGER.info(f"Successfully fetched repos from {INTEGRATION_NAME}")

        repos_object_names = [repo_object.repo for repo_object in repos_objects]

        siemplify.LOGGER.info("Extract repos addresses and check that all repos exists")
        existed_repos_addresses = [
            repo_object.address
            for repo_object in repos_objects
            if repo_object.repo in repos
        ]

        not_existed_repos_addresses = [
            repo for repo in repos if repo not in repos_object_names
        ]

        if not_existed_repos_addresses:
            siemplify.LOGGER.info("At least one repo not exists")
            raise LogPointInvalidParametersException(
                f"The following "
                f"repos were not found in {INTEGRATION_NAME}: "
                f"{', '.join(not_existed_repos_addresses)}. Please make sure "
                "that all of the repos are available."
            )

        repos_addresses = existed_repos_addresses

    siemplify.LOGGER.info("Creates Query Job")
    query_job = manager.create_query_job(
        time_range=time_range, query=query, limit=limit, repos=repos_addresses
    )

    if query_job.success:
        output_message += (
            f"Waiting for query to finish processing in {INTEGRATION_NAME}."
        )
        result_value = json.dumps({SEARCH_ID: query_job.search_id})

    else:
        output_message += (
            f"Action wasn’t able to successfully execute query and retrieve results "
            f"from {INTEGRATION_NAME}. "
        )
        result_value = False
        status = EXECUTION_STATE_COMPLETED

    return output_message, result_value, status


def query_operation_status(siemplify, manager, search_id):
    siemplify.LOGGER.info(f"Execute query with search_id: {search_id}")
    query_result = manager.get_query_results(search_id=search_id)

    if not query_result.finished:
        siemplify.LOGGER.info("Query execution still in progress")
        status = EXECUTION_STATE_INPROGRESS
        result_value = json.dumps({SEARCH_ID: search_id})
        output_message = (
            f"Waiting for query to finish processing in {INTEGRATION_NAME}."
        )

    else:
        siemplify.LOGGER.info("Query execution was done!")
        output_message, result_value, status = finish_operation(
            siemplify=siemplify, query_result=query_result
        )

    return output_message, result_value, status


def finish_operation(siemplify, query_result):
    json_results = []
    csv_table = []
    query_rows = query_result.query_rows

    if query_result.query_rows:
        for query_row in query_rows:
            json_results.append(query_row.raw_data)
            csv_table.append(query_row.raw_data)

        if json_results and csv_table:
            siemplify.result.add_result_json(json_results)
            siemplify.result.add_data_table(
                title=RESULTS, data_table=construct_csv(csv_table)
            )

        result_value = True
        output_message = (
            "Successfully executed query and retrieved results from "
            f"{INTEGRATION_NAME}."
        )

    else:
        output_message = f"No data was found for the provided query."
        result_value = False

    status = EXECUTION_STATE_COMPLETED
    return output_message, result_value, status


@output_handler
def main(is_first_run):
    siemplify = SiemplifyAction()
    siemplify.script_name = f"{INTEGRATION_NAME} - {EXECUTE_QUERY}"
    siemplify.LOGGER.info("================= Main - Param Init =================")

    ip_address = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="IP Address",
        is_mandatory=True,
        print_value=True,
    )

    username = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Username",
        is_mandatory=True,
        print_value=True,
    )

    secret = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Secret",
        is_mandatory=True,
    )

    ca_certificate_file = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="CA Certificate File",
        is_mandatory=False,
    )

    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        input_type=bool,
        default_value=True,
        is_mandatory=True,
        print_value=True,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    try:
        manager = LogPointManager(
            ip_address=ip_address,
            username=username,
            secret=secret,
            ca_certificate_file=ca_certificate_file,
            verify_ssl=verify_ssl,
        )
        manager.test_connectivity()

        if is_first_run:
            siemplify.LOGGER.info("First Run")
            output_message, result_value, status = start_operation(
                siemplify=siemplify, manager=manager
            )

        elif unix_now() >= siemplify.execution_deadline_unix_time_ms:
            siemplify.LOGGER.error(
                "Action reached a timeout. Please narrow down the time frame or lower "
                "the amount of results to return."
            )
            status = EXECUTION_STATE_TIMEDOUT
            result_value = False
            output_message = (
                "Action reached a timeout. Please narrow down the time "
                "frame or lower the amount of results to return."
            )

        else:
            siemplify.LOGGER.info("Not the first run")
            search_id = json.loads(
                siemplify.extract_action_param("additional_data")
            ).get(SEARCH_ID)
            output_message, result_value, status = query_operation_status(
                siemplify=siemplify, manager=manager, search_id=search_id
            )

    except Exception as error:
        result_value = False
        status = EXECUTION_STATE_FAILED
        output_message = (
            f'Error executing action "{EXECUTE_QUERY}". Reason: {error}'
            f"{INTEGRATION_NAME}. Reason: {error}"
        )
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
