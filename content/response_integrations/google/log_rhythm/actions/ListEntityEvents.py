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
import sys
import json
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyUtils import unix_now, output_handler, convert_dict_to_json_result_dict
from soar_sdk.ScriptResult import (
    EXECUTION_STATE_COMPLETED,
    EXECUTION_STATE_FAILED,
    EXECUTION_STATE_INPROGRESS,
)
from ..core.LogRhythmManager import LogRhythmRESTManager
from TIPCommon import extract_configuration_param, extract_action_param, construct_csv
from ..core.constants import (
    INTEGRATION_NAME,
    LIST_ENTITY_EVENTS_SCRIPT_NAME,
    SORT_ORDER_MAPPING,
    TIME_FRAME_MAPPING,
)
from ..core.utils import (
    get_entity_original_identifier,
    validate_positive_integer,
    is_async_action_global_timeout_approaching,
)
from datetime import datetime
from ..core.LogRhythmParser import LogRhythmParser

SUPPORTED_ENTITIES = [
    EntityTypes.ADDRESS,
    EntityTypes.HOSTNAME,
    EntityTypes.URL,
    EntityTypes.FILEHASH,
    EntityTypes.USER,
    EntityTypes.CVE,
]

FAILED_STATUS = "Search Failed"
COMPLETED_STATUS = "Completed"


def start_operation(siemplify, manager, start_time, end_time, suitable_entities, limit):
    sort_order = extract_action_param(
        siemplify,
        param_name="Sort Order",
        default_value="Inserted Time ASC",
        print_value=True,
    )
    sort_order = SORT_ORDER_MAPPING.get(sort_order)
    output_message = ""
    status = EXECUTION_STATE_INPROGRESS
    result_value = {"in_progress": {}, "completed": {}, "failed": []}
    successful_entities, failed_entities = [], []
    for entity in suitable_entities:
        entity_identifier = get_entity_original_identifier(entity)
        try:
            task = manager.execute_search(
                entity_identifier=entity_identifier,
                entity_type=entity.entity_type,
                start_time=start_time,
                end_time=end_time,
                sort_order=sort_order,
                limit=limit,
            )

            result_value["in_progress"][entity_identifier] = task.id
            successful_entities.append(entity_identifier)
        except Exception as err:
            failed_entities.append(entity_identifier)
            result_value["failed"].append(entity_identifier)
            siemplify.LOGGER.error(
                f"An error occurred when initiate query for entity {entity_identifier}:"
                f" Reason {err}"
            )
            siemplify.LOGGER.exception(err)

    if successful_entities:
        result_value = json.dumps(result_value)
        output_message = (f"Successfully retrieved events for the following entities "
                          f"in {INTEGRATION_NAME}")
    else:
        output_message = (f"Action wasn't able to retrieve events for the provided "
                          f"entities in {INTEGRATION_NAME}. ")
        result_value = False
        status = EXECUTION_STATE_COMPLETED

    return output_message, result_value, status


def query_operation_status(
    siemplify, manager, action_start_time, result_data, suitable_entities, limit
):
    failed_entities, completed_entities = [], {}

    timeout_approaching = False

    for entity, task_id in result_data["in_progress"].items():
        if is_async_action_global_timeout_approaching(siemplify, action_start_time):
            siemplify.LOGGER.info("Timeout is approaching. Action will gracefully exit")
            timeout_approaching = True
            break
        siemplify.LOGGER.info(f"Checking status for {entity} with task id {task_id}.")
        try:
            task = manager.get_search_results(task_id=task_id, limit=limit)
            if COMPLETED_STATUS in task.status:
                completed_entities[entity] = task.raw_data
            elif task.status == FAILED_STATUS:
                failed_entities.append(entity)
                result_data["failed"].append(entity)
        except Exception as err:
            failed_entities.append(entity)
            result_data["failed"].append(entity)
            siemplify.LOGGER.error(
                f"An error occurred when getting data about task {task_id}"
            )
            siemplify.LOGGER.exception(err)
    for key in completed_entities.keys():
        result_data["in_progress"].pop(key)
    for entity in failed_entities:
        result_data["in_progress"].pop(entity)
    result_data["completed"].update(completed_entities)
    if result_data["in_progress"] and not timeout_approaching:
        status = EXECUTION_STATE_INPROGRESS
        result_value = json.dumps(result_data)
        output_message = (
            f"Waiting for events information for the following entities: "
            f"{', '.join(result_data['in_progress'].keys())}"
        )

    else:
        output_message, result_value, status = finish_operation(
            siemplify=siemplify,
            result_data=result_data,
            suitable_entities=suitable_entities,
            timeout_approaching=timeout_approaching,
        )

    return output_message, result_value, status


def finish_operation(siemplify, result_data, suitable_entities, timeout_approaching):
    parser = LogRhythmParser()
    result_value = True
    status = EXECUTION_STATE_COMPLETED
    output_message = ""
    failed_entities = result_data["failed"]
    not_finished, successful_entities, no_data, csv_output, json_result = (
        [],
        [],
        [],
        [],
        {},
    )
    for entity in suitable_entities:
        entity_identifier = get_entity_original_identifier(entity)
        if entity_identifier in result_data["completed"].keys():
            task = parser.build_task_obj(result_data["completed"][entity_identifier])
            if not task.events:
                no_data.append(entity_identifier)
            else:
                json_result[entity_identifier] = [
                    event.as_json() for event in task.events
                ]
                csv_output = [event.to_csv() for event in task.events]
                siemplify.result.add_entity_table(
                    entity_identifier, construct_csv(csv_output)
                )
                successful_entities.append(entity_identifier)
        if entity_identifier in result_data["in_progress"].keys():
            not_finished.append(entity_identifier)

    if no_data:
        output_message += (
            f"No events were found for the following entities in "
            f"{INTEGRATION_NAME}: {', '.join(no_data)}\n"
        )
    if failed_entities:
        output_message += (
            f"Action wasn't able to retrieve events for the following entities in "
            f"{INTEGRATION_NAME}: {', '.join(failed_entities)} \n"
        )
    if successful_entities:
        output_message += (
            f"Successfully retrieved events for the following entities in "
            f"{INTEGRATION_NAME}: {', '.join(successful_entities)}\n"
        )
    if timeout_approaching and not_finished:
        if not output_message:
            raise Exception(
                f"Action ran into a timeout during execution. No information about the "
                f"events was retrieved for the provided entities. "
                f"Please increase the action timeout in the IDE"
            )
        else:
            output_message += (
                f"Action ran into a timeout during execution. Pending entities: "
                f"{','.join(not_finished)}. Please increase the timeout in the IDE."
            )
    elif no_data and not failed_entities:
        output_message = (
            f"No events were found for the provided entities in {INTEGRATION_NAME}."
        )
        result_value = False
    elif not no_data and failed_entities:
        output_message = (f"Action wasn't able to retrieve events for the "
                          f"provided entities in {INTEGRATION_NAME}.")
        result_value = False

    if json_result:
        siemplify.result.add_result_json(convert_dict_to_json_result_dict(json_result))

    return output_message, result_value, status


@output_handler
def main(is_first_run):
    siemplify = SiemplifyAction()
    action_start_time = unix_now()
    siemplify.script_name = LIST_ENTITY_EVENTS_SCRIPT_NAME
    mode = "Main" if is_first_run else "Get Report"

    siemplify.LOGGER.info(f"----------------- {mode} - Param Init -----------------")

    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Root",
        is_mandatory=True,
    )
    api_key = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Token",
        is_mandatory=True,
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        default_value=False,
        input_type=bool,
    )

    time_frame = extract_action_param(
        siemplify, param_name="Time Frame", default_value="Last Hour", print_value=True
    )
    start_time = extract_action_param(
        siemplify, param_name="Start Time", print_value=True
    )
    end_time = extract_action_param(siemplify, param_name="End Time", print_value=True)

    limit = extract_action_param(
        siemplify,
        param_name="Max Events To Return",
        default_value=50,
        print_value=True,
        input_type=int,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    status = EXECUTION_STATE_INPROGRESS
    result_value = False
    output_message = ""
    suitable_entities = [
        entity
        for entity in siemplify.target_entities
        if entity.entity_type in SUPPORTED_ENTITIES
    ]
    time_frame = TIME_FRAME_MAPPING.get(time_frame)
    try:
        if time_frame is None and start_time is None:
            raise Exception(
                "'Start Time' should be provided, when 'Custom' is selected in the "
                "'Time Frame' parameter."
            )
        if time_frame is None and end_time is None:
            end_time = datetime.fromtimestamp(int(unix_now() / 1000)).isoformat()
        if start_time and end_time and start_time > end_time:
            raise Exception("'End Time' should be later than 'Start Time'")
        validate_positive_integer(
            limit, err_msg="'Max Events To Return' should be greater than 0."
        )
        manager = LogRhythmRESTManager(
            api_root=api_root,
            api_key=api_key,
            verify_ssl=verify_ssl,
            force_check_connectivity=True,
        )
        if time_frame:
            start_time = datetime.fromtimestamp(
                int((unix_now() - time_frame) / 1000)
            ).isoformat()
            end_time = datetime.fromtimestamp(int(unix_now() / 1000)).isoformat()
        if is_first_run:
            output_message, result_value, status = start_operation(
                siemplify,
                manager=manager,
                start_time=start_time,
                end_time=end_time,
                suitable_entities=suitable_entities,
                limit=limit,
            )
        if status == EXECUTION_STATE_INPROGRESS:
            sessions = (
                result_value
                if result_value
                else extract_action_param(
                    siemplify, param_name="additional_data", default_value="{}"
                )
            )
            output_message, result_value, status = query_operation_status(
                siemplify=siemplify,
                manager=manager,
                action_start_time=action_start_time,
                result_data=json.loads(sessions),
                suitable_entities=suitable_entities,
                limit=limit,
            )

    except Exception as e:
        output_message = (
            f"Error executing action {LIST_ENTITY_EVENTS_SCRIPT_NAME}. Reason: {e}"
        )
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        result_value = False

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  "
        f"is_success: {result_value}\n  "
        f"output_message: {output_message}"
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    is_first_run = len(sys.argv) < 3 or sys.argv[2] == "True"
    main(is_first_run)
