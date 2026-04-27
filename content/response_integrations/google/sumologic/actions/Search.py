from __future__ import annotations
import json
import sys

import arrow
from TIPCommon import extract_configuration_param, extract_action_param

from soar_sdk.ScriptResult import (
    EXECUTION_STATE_COMPLETED,
    EXECUTION_STATE_INPROGRESS,
    EXECUTION_STATE_FAILED,
)
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import construct_csv
from soar_sdk.SiemplifyUtils import output_handler
from ..core.SumoLogicManager import SumoLogicManager
from ..core.consts import (
    SEARCH_SCRIPT_NAME,
    INTEGRATION_NAME,
    INTEGRATION_IDENTIFIER,
    DEFAULT_SINCE_TIME_DAYS,
    DEFAULT_MAX_SEARCH_JOB_RESULTS,
)


def start_operation(
    siemplify: SiemplifyAction,
    sumologic_manager: SumoLogicManager,
    query: str,
    since: str,
    to: str,
):
    """
    Create search job
    :param siemplify: {SiemplifyAction} SiemplifyAction instance
    :param sumologic_manager: {SumologicManager} Sumologic manager
    :param query: {str} The actual search expression. Make sure your query
        is in valid JSON format, you may need to escape certain characters.
    :param since: {str} The ISO 8601 date and time of the time range to start the search.
        Can be unixtime (milliseconds) or YYYY-MM-DDTHH:mm:ss. Milliseconds can be provided as int.
    :param to: {str} The ISO 8601 date and time of the time range to end the search.
        Can be unixtime (milliseconds) or YYYY-MM-DDTHH:mm:ss. Milliseconds can be provided as int.
    :return: {output message, json result, execution_state}
    """
    try:
        siemplify.LOGGER.info(f"Running search with query: {query}")
        job_id = sumologic_manager.search(query, since=since, to=to)
        siemplify.LOGGER.info(f"Search job ID: {job_id}")

        result_value = json.dumps(job_id)
        output_message = f"Search {job_id} initiated. Waiting for completion."
        status = EXECUTION_STATE_INPROGRESS

    except Exception as error:
        output_message = (
            f"Failed to create search job in {INTEGRATION_NAME}! Error is: {error}"
        )
        siemplify.LOGGER.exception(error)
        siemplify.LOGGER.error(output_message)
        result_value = False
        status = EXECUTION_STATE_FAILED

    return output_message, result_value, status


def query_operation_status(
    siemplify: SiemplifyAction,
    sumologic_manager: SumoLogicManager,
    job_id: str,
    delete_search_job: bool,
    limit: int,
):
    """
    Get query results
    :param siemplify: {SiemplifyAction} SiemplifyAction instance
    :param sumologic_manager: {SumologicManager} Sumologic manager
    :param job_id: {str} Job id to query results from
    :param delete_search_job: {bool} True if searched job should be deleted, otherwise False
    :param limit: {int} Max number of results to return
    :return: {output message, json result, execution_state}
    """
    try:
        job = sumologic_manager.get_job_info(job_id)

        if not job.completed:
            if job.failed:
                output_message = f"Search {job_id} has failed: {job.state}"
                result_value = json.dumps([])
                status = EXECUTION_STATE_FAILED
            else:
                # Pending for completion
                output_message = f"Search {job_id} is not complete: {job.state}"
                result_value = json.dumps(job_id)
                status = EXECUTION_STATE_INPROGRESS

        else:
            siemplify.LOGGER.info(f"Search {job_id} completed. Collecting results.")
            search_messages = sumologic_manager.get_latest_search_results(job_id, limit)
            siemplify.LOGGER.info(f"Found {len(search_messages)} results.")

            if search_messages:
                # Add results
                siemplify.result.add_data_table(
                    f"Results - Total {len(search_messages)}",
                    construct_csv([message.as_csv() for message in search_messages]),
                )
                siemplify.result.add_result_json(
                    json.dumps([message.as_json() for message in search_messages])
                )

            output_message = f"Search completed. Found {len(search_messages)} results"
            status = EXECUTION_STATE_COMPLETED
            result_value = json.dumps(
                [message.as_json() for message in search_messages]
            )

        if delete_search_job and (job.completed or job.failed):
            sumologic_manager.delete_job(job_id)
            siemplify.LOGGER.info(f"Deleted search job {job_id}")

    except Exception as error:
        output_message = (
            f"Failed to query for results in {INTEGRATION_NAME}! Error is: {error}"
        )
        siemplify.LOGGER.exception(error)
        siemplify.LOGGER.error(output_message)
        result_value = False
        status = EXECUTION_STATE_FAILED

    return output_message, result_value, status


@output_handler
def main(is_first_run):
    siemplify = SiemplifyAction()
    siemplify.script_name = f"{INTEGRATION_IDENTIFIER} - {SEARCH_SCRIPT_NAME}"
    mode = "Main" if is_first_run else "Check changes"
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    # Integration Configuration
    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_IDENTIFIER,
        param_name="Api Root",
        is_mandatory=True,
        print_value=True,
    )
    access_id = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_IDENTIFIER,
        param_name="Access ID",
        is_mandatory=True,
        print_value=True,
    )
    access_key = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_IDENTIFIER,
        param_name="Access Key",
        is_mandatory=True,
        print_value=False,
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_IDENTIFIER,
        param_name="Verify SSL",
        default_value=False,
        input_type=bool,
        print_value=True,
        is_mandatory=True,
    )

    siemplify.LOGGER.info(f"----------------- {mode} - Started -----------------")

    try:
        # Action configuration
        query = extract_action_param(
            siemplify, param_name="Query", is_mandatory=True, print_value=True
        )
        since = extract_action_param(
            siemplify,
            param_name="Since",
            is_mandatory=False,
            default_value=None,
            print_value=True,
        )
        to = extract_action_param(
            siemplify,
            param_name="To",
            is_mandatory=False,
            default_value=None,
            print_value=True,
        )
        limit = extract_action_param(
            siemplify,
            param_name="Limit",
            is_mandatory=False,
            default_value=DEFAULT_MAX_SEARCH_JOB_RESULTS,
            print_value=True,
            input_type=int,
        )
        delete_search_job = extract_action_param(
            siemplify,
            param_name="Delete Search Job",
            is_mandatory=False,
            print_value=True,
            input_type=bool,
            default_value=False,
        )

        sumologic_manager = SumoLogicManager(
            server_address=api_root,
            access_id=access_id,
            access_key=access_key,
            verify_ssl=verify_ssl,
            logger=siemplify.LOGGER,
        )

        if is_first_run:
            if not since:
                since = (
                    arrow.utcnow().shift(days=-DEFAULT_SINCE_TIME_DAYS).int_timestamp * 1000
                )
                siemplify.LOGGER.info(
                    f'"Since" parameter was not provided. Using default value of {since}'
                )

            if not to:
                to = arrow.utcnow().int_timestamp * 1000
                siemplify.LOGGER.info(
                    f'"To" parameter was not provided. Using default value of {to}'
                )

            output_message, result_value, status = start_operation(
                siemplify, sumologic_manager, query, since, to
            )
        else:
            if limit <= 0:
                siemplify.LOGGER.info(
                    f'"Limit" parameter must be non-negative. Using default of {DEFAULT_MAX_SEARCH_JOB_RESULTS}'
                )
                limit = DEFAULT_MAX_SEARCH_JOB_RESULTS

            job_id = json.loads(siemplify.extract_action_param("additional_data"))
            output_message, result_value, status = query_operation_status(
                siemplify, sumologic_manager, job_id, delete_search_job, limit
            )

    except Exception as error:
        output_message = (
            f'Error executing action "{SEARCH_SCRIPT_NAME}". Reason: {error}'
        )
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(error)
        status = EXECUTION_STATE_FAILED
        result_value = False

    siemplify.LOGGER.info(f"----------------- {mode} - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}:")
    siemplify.LOGGER.info(f"Result Value: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    is_first_run = len(sys.argv) < 3 or sys.argv[2] == "True"
    main(is_first_run)
