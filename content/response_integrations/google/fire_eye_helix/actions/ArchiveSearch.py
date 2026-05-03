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
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyAction import SiemplifyAction
from ..core.FireEyeHelixConstants import PROVIDER_NAME, ARCHIVE_SEARCH_SCRIPT_NAME
from TIPCommon import extract_configuration_param, extract_action_param
from ..core.FireEyeHelixManager import FireEyeHelixManager
from soar_sdk.ScriptResult import (
    EXECUTION_STATE_COMPLETED,
    EXECUTION_STATE_FAILED,
    EXECUTION_STATE_INPROGRESS,
)
from ..core.FireEyeHelixExceptions import (
    FireEyeHelixJobNotFinishedException,
    FireEyeHelixJobPausedException,
)
import json
import sys


def start_operation(siemplify, manager, query, time_frame, limit, paused_count):
    """
    Start archive search query.
    :param siemplify: SiemplifyAction object.
    :param manager: FireEyeHelixManager object.
    :param query: {str} The query for the search.
    :param time_frame: {str} The time frame for the search.
    :param limit: {int} Maximum number of results to return.
    :param paused_count: {int} Specify how many times job was paused.
    :return: {tuple} output message, json result, execution state
    """
    job_id = manager.initialize_archive_search_query(query, time_frame)
    # If api return job data almost instantly here we will try to get data.
    return query_operation_status(
        siemplify, manager, job_id, query, limit, paused_count
    )


def query_operation_status(siemplify, manager, job_id, query, limit, paused_count):
    """
    Query archive search results.
    :param siemplify: SiemplifyAction object.
    :param manager: FireEyeHelixManager object.
    :param job_id: {int} The job id to fetch data.
    :param query: {str} The query for the search.
    :param limit: {int} Maximum number of results to return.
    :param paused_count: {int} Specify how many times job was paused.
    :return: {tuple} output message, json result, execution state
    """
    try:
        result = manager.get_query_result(job_id, limit)

        if result.contains_results():
            output_message = f'Successfully returned results for the archive query "{query}" in {PROVIDER_NAME}.'
            result_value = True
            siemplify.result.add_result_json(result.to_json())
        else:
            output_message = f'No results were found for the archive query "{query}".'
            result_value = False

        state = EXECUTION_STATE_COMPLETED

    except FireEyeHelixJobNotFinishedException:
        output_message = "Continuing processing query"
        result_value = json.dumps([job_id, paused_count])
        state = EXECUTION_STATE_INPROGRESS
    except FireEyeHelixJobPausedException:
        if paused_count < 3:
            paused_count += 1
            manager.resume_archive_search_query(job_id)
            output_message = "Archive search job was resumed"
            result_value = json.dumps([job_id, paused_count])
            state = EXECUTION_STATE_INPROGRESS
        else:
            output_message = (
                'No results were found for the archive query "{}". '
                "Reason: archive search job was paused more than 3 times.".format(query)
            )
            result_value = False
            state = EXECUTION_STATE_COMPLETED

    return output_message, result_value, state


@output_handler
def main(is_first_run):
    siemplify = SiemplifyAction()
    siemplify.script_name = ARCHIVE_SEARCH_SCRIPT_NAME
    mode = "Main" if is_first_run else "QueryState"

    siemplify.LOGGER.info(f"----------------- {mode} - Param Init -----------------")

    # Init Integration Configurations
    api_root = extract_configuration_param(
        siemplify, provider_name=PROVIDER_NAME, param_name="API Root", is_mandatory=True
    )

    api_token = extract_configuration_param(
        siemplify,
        provider_name=PROVIDER_NAME,
        param_name="API Token",
        is_mandatory=True,
    )

    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=PROVIDER_NAME,
        param_name="Verify SSL",
        is_mandatory=True,
        input_type=bool,
    )

    # Init Action Parameters
    query = extract_action_param(
        siemplify, param_name="Query", is_mandatory=True, print_value=True
    )
    time_frame = extract_action_param(
        siemplify, param_name="Time Frame", is_mandatory=True, print_value=True
    )
    limit = extract_action_param(
        siemplify,
        param_name="Max Results To Return",
        is_mandatory=False,
        input_type=int,
        print_value=True,
    )

    siemplify.LOGGER.info(f"----------------- {mode} - Started -----------------")

    try:
        manager = FireEyeHelixManager(
            api_root=api_root,
            api_token=api_token,
            verify_ssl=verify_ssl,
            siemplify=siemplify,
        )

        if is_first_run:
            paused_count = 0
            output_message, result_value, status = start_operation(
                siemplify, manager, query, time_frame, limit, paused_count
            )
        else:
            job_id, paused_count = json.loads(siemplify.parameters["additional_data"])
            output_message, result_value, status = query_operation_status(
                siemplify, manager, job_id, query, limit, paused_count
            )

    except Exception as e:
        siemplify.LOGGER.exception(e)
        output_message = f'Error executing action "Archive Search". Reason: {e}\''
        status = EXECUTION_STATE_FAILED
        result_value = False

    siemplify.LOGGER.info(f"----------------- {mode} - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"Result: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")

    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    is_first_run = len(sys.argv) < 3 or sys.argv[2] == "True"
    main(is_first_run)
