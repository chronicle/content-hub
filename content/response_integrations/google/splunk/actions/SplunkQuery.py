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

from typing import Any, Dict
import dataclasses
import json
import sys
import time
from copy import deepcopy
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.ScriptResult import (
    EXECUTION_STATE_COMPLETED,
    EXECUTION_STATE_INPROGRESS,
    EXECUTION_STATE_FAILED,
)
from TIPCommon.extraction import extract_configuration_param, extract_action_param
from TIPCommon.transformation import construct_csv
from splunk.core import constants
from splunk.core.datamodels import JobDetail
from splunk.core.exceptions import (
    AdhocSearchLevelException,
    SplunkBadRequestException,
    SplunkHTTPException,
)
from splunk.core import UtilsManager
from splunk.core.SplunkManager import SplunkManager


SingleJson = Dict[str, Any]


@dataclasses.dataclass
class ActionData:
    pending_queries: dict
    successful_queries: dict
    unsuccessful_queries: list
    failed_queries: list


def start_operation(
    siemplify: SiemplifyAction,
    manager: SplunkManager,
    search_mode: str,
    queries: list,
    result_fields: list,
    limit: int,
    queries_result: SingleJson,
) -> tuple[str, int]:
    """Start an operation with specified parameters.

    Args:
        siemplify (SiemplifyAction): An instance of the SiemplifyAction class.
        manager (SplunkManager): An instance of SplunkManager responsible for managing
            Splunk operations.
        search_mode (str): The mode of search operation.
            e.g. - Smart, Verbose, Fast
        queries (list): A list of queries to be executed.
        result_fields (list): A list of fields to filter the query JSON result.
        limit (int): The maximum number of results to retrieve.
        queries_result (SingleJson): A dictionary containing the results of the queries.
    """
    pending_queries = {}
    from_time = extract_action_param(
        siemplify,
        param_name="Results From",
        default_value=constants.FROM_TIME_DEFAULT,
        print_value=True,
    )
    to_time = extract_action_param(
        siemplify,
        param_name="Results To",
        default_value=constants.TO_TIME_DEFAULT,
        print_value=True,
    )
    for query in queries:
        try:
            job_sid = manager.search_job_for_query(
                search_mode=search_mode,
                query=query,
                limit=limit,
                from_time=from_time,
                to_time=to_time,
                fields=result_fields,
            )
            pending_queries[query] = job_sid
            siemplify.LOGGER.info(f"Successfully started searching query: {query}")

        except (SplunkBadRequestException, SplunkHTTPException) as e:
            siemplify.LOGGER.error(f'Error executing query "{query}": Reason: {e}')
            queries_result.failed_queries.append(query)

    queries_result.pending_queries = pending_queries


def query_operation_status(
    siemplify: SiemplifyAction,
    manager: SplunkManager,
    queries_result: SingleJson,
    result_fields: list,
    limit: int,
) -> tuple(str, bool | str, int):
    """Check the status of query operations and handle pending queries.

    Args:
        siemplify (SiemplifyAction): An instance of the SiemplifyAction class.
        manager (SplunkManager): An instance of SplunkManager responsible for managing
            Splunk operations.
        result (SingleJson): A dictionary containing the result of query operations.
        result_fields (list): A list of fields to include in the result.
        limit (int): The maximum number of results to retrieve.

    Returns:
        tuple[str, bool | SingleJson, int]: A tuple containing:
            - output_message (str): A message indicating the outcome of the operation.
            - result_value (bool | str): The updated json result or a boolean
                indicating the operation status.
            - status (int): The execution status of the operation.
    """
    query_result_data = deepcopy(dataclasses.asdict(queries_result))

    for query, sid in queries_result.pending_queries.items():
        if wait_and_check_if_job_id_done(manager, query, sid):
            result_json = finish_query_operation(manager, sid, limit)
            if result_json:
                query_result_data["successful_queries"][query] = result_json
            else:
                query_result_data["unsuccessful_queries"].append(query)
            query_result_data["pending_queries"].pop(query, None)

    return finish_operation(
        siemplify=siemplify,
        query_result_data=query_result_data,
        result_fields=result_fields,
    )


def wait_and_check_if_job_id_done(manager: SplunkManager, query: str, sid: str):
    """Wait and check if Query job SID is done.

    Args:
        manager (SplunkManager): An instance of SplunkManager responsible for managing
            Splunk operations.
        query (str): Splunk Search query to check the status.
        sid (str): The unique identifier for the query search job.

    Returns:
        bool: True if the job is done, False otherwise.
    """
    for _ in range(constants.MAX_ATTEMPT_FOR_JOB_RESULT):
        if manager.is_job_done(sid=sid):
            manager.siemplify_logger.info(f"Query executed successfully: {query}")
            return True
        manager.siemplify_logger.info(f"Waiting for the query completion: {query}")
        time.sleep(3)

    manager.siemplify_logger.info(f"Query execution is in progress: {query}")

    return False


def finish_query_operation(
    manager: SplunkManager, sid: str, limit: int
) -> list[SingleJson]:
    """Finish the operation by retrieving job results and generating an output message.

    Args:
        manager (SplunkManager): An instance of SplunkManager responsible for managing
            Splunk operations.
        sid (str): The unique identifier for the job in Splunk.
        limit (int): The maximum number of results to retrieve.

    Returns:
        list[SingleJson]: list the query results.
    """
    result_json = []
    job_details = manager.get_job_results(sid, limit=limit)
    if job_details:
        result_json = [job_detail.to_json() for job_detail in job_details]

    manager.delete_job(sid=sid)

    return result_json


def finish_operation(
    siemplify: SiemplifyAction, query_result_data: SingleJson, result_fields: list[str]
) -> tuple[str, bool | str, int]:
    """Finish the operation by processing query results.

    Args:
        siemplify: The SiemplifyAction instance.
        query_result_data (SingleJson): A dictionary containing the result of the
            queries.
        result_fields (list[str]): A list of fields to create the table.

    Returns:
        tuple[str, bool | str, int]: A tuple containing:
            - output_message (str): A message indicating the outcome of the operation.
            - result_value (bool | str): The updated result or a string indicating the
               operation status.
            - status (int): The execution status of the operation.
    """
    if query_result_data["pending_queries"]:
        return (
            _generate_inprogress_output_message(query_result_data),
            json.dumps(query_result_data),
            EXECUTION_STATE_INPROGRESS,
        )

    if query_result_data["successful_queries"]:
        siemplify.result.add_result_json(
            set_json_result(query_result_data["successful_queries"])
        )
        table_data = construct_csv(
            set_table_result(query_result_data["successful_queries"], result_fields)
        )
        siemplify.result.add_data_table(constants.QUERY_RESULTS_TABLE_NAME, table_data)
        return (
            _generate_success_output_message(query_result_data),
            True,
            EXECUTION_STATE_COMPLETED,
        )

    if query_result_data["unsuccessful_queries"]:
        output_message = (
            _generate_success_output_message(query_result_data)
            if query_result_data["failed_queries"]
            else _generate_unsuccessful_output_message()
        )
        return (output_message, False, EXECUTION_STATE_COMPLETED)

    return (_generate_failure_output_message(), False, EXECUTION_STATE_FAILED)


def set_json_result(json_result: SingleJson) -> list[SingleJson]:
    """Modify a JSON result by adding a 'chronicle_query_used' key to each result.

    Args:
        json_result (SingleJson): A dictionary containing query results.

    Returns:
        list[SingleJson]: A list of dictionaries representing the modified JSON result,
            where each dictionary contains the added 'chronicle_query_used' key.
    """
    query_json_result = []
    for query, results in json_result.items():
        for result in results:
            result["chronicle_query_used"] = query
            query_json_result.append(result)

    return query_json_result


def set_table_result(
    json_result: SingleJson, result_fields: list[str]
) -> list[SingleJson]:
    """Generate a table result from a JSON result with specified result fields.

    Args:
        json_result (SingleJson): A dictionary containing query results.
        result_fields (list[str]): A list of fields to include in the table result.

    Returns:
        list[SingleJson]: A list of dictionaries representing the table result,
            where each dictionary contains filtered data based on the result fields.
    """
    table_result = []
    for query, results in json_result.items():
        table_data = []
        for result in results:
            csv_result = JobDetail.from_json(result).to_filtered_csv(result_fields)
            csv_result["chronicle_query_used"] = query
            table_data.append(csv_result)

        table_result.extend(table_data)

    return table_result


def _generate_success_output_message(query_result: SingleJson) -> str:
    message = ""
    success_queries = query_result["successful_queries"].keys()
    success_queries_str = " \n".join(success_queries)
    unsuccessful_queries = query_result["unsuccessful_queries"]
    unsuccessful_queries_str = " \n".join(unsuccessful_queries)
    failed_queries = query_result["failed_queries"]
    failed_queries_str = " \n".join(failed_queries)
    if success_queries:
        message += (
            "Successfully returned results for the following queries in "
            f"{constants.INTEGRATION_NAME}:\n{success_queries_str}"
        )
    if unsuccessful_queries:
        message += (
            "\nNo results were found for the following queries in "
            f"{constants.INTEGRATION_NAME}:\n{unsuccessful_queries_str}"
        )
    if failed_queries:
        message += (
            f"\nFailed to execute following queries in {constants.INTEGRATION_NAME}. "
            f"Please check the configuration:\n{failed_queries_str}"
        )

    return message.strip("\n")


def _generate_inprogress_output_message(query_result: SingleJson) -> str:
    return (
        "Waiting for following queries to finish execution."
        f'\n{", ".join(query_result["pending_queries"].keys())}'
    )


def _generate_unsuccessful_output_message() -> str:
    return (
        "No results were found for the provided queries in "
        f"{constants.INTEGRATION_NAME}."
    )


def _generate_failure_output_message() -> str:
    return (
        "Failed to execute all of the provided queries. Please check the configuration."
    )


@output_handler
def main(is_first_run):
    siemplify = SiemplifyAction()
    siemplify.script_name = constants.SPLUNK_QUERY_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    # Configuration Parameters
    url = extract_configuration_param(
        siemplify,
        provider_name=constants.INTEGRATION_NAME,
        param_name="Api Root",
        print_value=True,
    )
    username = extract_configuration_param(
        siemplify, provider_name=constants.INTEGRATION_NAME, param_name="Username"
    )
    password = extract_configuration_param(
        siemplify, provider_name=constants.INTEGRATION_NAME, param_name="Password"
    )
    api_token = extract_configuration_param(
        siemplify, provider_name=constants.INTEGRATION_NAME, param_name="API Token"
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=constants.INTEGRATION_NAME,
        param_name="Verify SSL",
        print_value=True,
        input_type=bool,
    )
    # Action Parameters
    query = extract_action_param(
        siemplify, param_name="Query", print_value=True, is_mandatory=True
    )
    search_mode = extract_action_param(
        siemplify,
        param_name="Search Mode",
        print_value=True,
        is_mandatory=False,
        default_value="Smart",
    )
    result_fields = extract_action_param(
        siemplify, param_name="Result fields", print_value=True
    )
    limit = extract_action_param(
        siemplify,
        param_name="Results count limit",
        input_type=int,
        default_value=constants.DEFAULT_QUERY_LIMIT,
        print_value=True,
    )
    ca_certificate = extract_configuration_param(
        siemplify,
        provider_name=constants.INTEGRATION_NAME,
        param_name="CA Certificate File",
    )
    additional_data = extract_action_param(
        siemplify, param_name="additional_data", default_value="{}"
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    queries_result = ActionData(
        pending_queries={},
        successful_queries={},
        unsuccessful_queries=[],
        failed_queries=[],
    )
    queries_result = json.loads(additional_data) or dataclasses.asdict(queries_result)
    queries_result = ActionData(**queries_result)
    try:
        manager = SplunkManager(
            server_address=url,
            username=username,
            password=password,
            api_token=api_token,
            ca_certificate=ca_certificate,
            verify_ssl=verify_ssl,
            siemplify_logger=siemplify.LOGGER,
        )
        queries = UtilsManager.get_splunk_queries(query)
        if is_first_run:
            start_operation(
                siemplify,
                manager=manager,
                search_mode=search_mode,
                queries=queries,
                result_fields=result_fields,
                limit=limit,
                queries_result=queries_result,
            )

        output_message, result_value, status = query_operation_status(
            siemplify=siemplify,
            manager=manager,
            queries_result=queries_result,
            result_fields=result_fields,
            limit=limit,
        )

    except AdhocSearchLevelException:
        output_message = (
            f"Error executing action {constants.SPLUNK_QUERY_SCRIPT_NAME}."
            "Reason: Wrong input Search Mode"
        )
        status = EXECUTION_STATE_FAILED
        result_value = False
        siemplify.LOGGER.error(output_message)

    except Exception as e:
        output_message = (
            f"Error executing action {constants.SPLUNK_QUERY_SCRIPT_NAME}. Reason: {e}"
        )
        status = EXECUTION_STATE_FAILED
        result_value = False
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\nstatus: {status}\nresults: {result_value}\noutput_message: {output_message}"
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    is_first_run = len(sys.argv) < 3 or sys.argv[2] == "True"
    main(is_first_run)
