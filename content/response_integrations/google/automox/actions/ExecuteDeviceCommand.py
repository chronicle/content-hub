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
from soar_sdk.SiemplifyUtils import output_handler, convert_dict_to_json_result_dict, unix_now
from soar_sdk.ScriptResult import (
    EXECUTION_STATE_COMPLETED,
    EXECUTION_STATE_INPROGRESS,
    EXECUTION_STATE_FAILED,
)

from soar_sdk.SiemplifyAction import SiemplifyAction
from TIPCommon import (
    extract_action_param,
    extract_configuration_param,
    convert_comma_separated_to_list,
)

from ..core.AutomoxManager import AutomoxManager
from ..core.AutomoxUtils import get_entity_original_identifier
from ..core.constants import (
    INTEGRATION_NAME,
    EXECUTE_DEVICE_COMMAND_SCRIPT_NAME,
    SUPPORTED_ENTITIES,
    ENTITY_MAPPER,
    COMMANDS_MAPPER,
)


import time
import json
import sys


def start_operation(siemplify, manager, command):
    status = EXECUTION_STATE_INPROGRESS

    tracked = []

    result_data = {
        "target_entities": [],
        "failed_entities": [],
        "successful_entities": {},
        "in_progress": [],
    }

    patch_names_string = extract_action_param(siemplify, param_name="Patch Names")
    patch_names = convert_comma_separated_to_list(patch_names_string)

    suitable_entities = [
        entity
        for entity in siemplify.target_entities
        if entity.entity_type in SUPPORTED_ENTITIES
    ]

    try:
        for entity in suitable_entities:
            result_data["target_entities"].append(entity.identifier)

            entity_original_identifier = get_entity_original_identifier(entity)

            devices = manager.get_devices(
                filter_value=entity_original_identifier,
                filter_field=ENTITY_MAPPER[entity.entity_type],
            )

            if not devices:
                siemplify.LOGGER.info(
                    f"Entity {entity.identifier} wasn't found on Automox"
                )
                result_data["failed_entities"].append(entity.identifier)
                continue

            device = devices[0]
            siemplify.LOGGER.info(
                f"Fetched device with id {device.id} for entity "
                f"{entity.identifier} from Automox"
            )

            if not device.connected:
                siemplify.LOGGER.info(
                    f"Device with id {device.id} is offline on Automox"
                )
                result_data["failed_entities"].append(entity.identifier)
                continue

            current_queue_items = manager.get_queue_data(device.id)

            # check if some of the commands are already in queue for a device
            current_queue_items = [
                item
                for item in current_queue_items
                if item.command_type_name == command
            ]
            if patch_names:
                current_queue_items = [
                    item.id for item in current_queue_items if item.args in patch_names
                ]

            if current_queue_items:
                siemplify.LOGGER.info(
                    f"Command {command} is already scheduled. Skipping tracking."
                )
                continue
            else:
                if patch_names:
                    for patch_name in patch_names:
                        manager.execute_device_command(device.id, command, patch_name)
                else:
                    manager.execute_device_command(device.id, command)
            # workaround for Automox items in a queue
            time.sleep(2)
            queue_items_after = manager.get_queue_data(device.id)

            if patch_names:
                queue_items_after = [
                    item.id
                    for item in queue_items_after
                    if item.command_type_name == command and item.args in patch_names
                ]
            else:
                queue_items_after = [
                    item.id
                    for item in queue_items_after
                    if item.command_type_name == command
                ]
            if not queue_items_after:
                siemplify.LOGGER.info(
                    f"Command {command} finished before we can find it in the queue. Skipping tracking."
                )
            else:
                tracked.append(
                    dict(
                        entity=entity.identifier,
                        device_id=device.id,
                        queue_items=queue_items_after,
                    )
                )

        if not tracked:
            output_message, result_data, status = finish_operation(
                siemplify=siemplify,
                result_data=result_data,
                timeout_approaching=False,
                command=command,
            )
            return output_message, result_data, status

        result_data["in_progress"].extend(tracked)
        result_data = json.dumps(result_data)
        output_message = (
            f"Waiting for commands execution to finish on the following entities: "
            f"{' '.join([item['entity'] for item in tracked])}"
        )
    except Exception as e:
        output_message = f"Error executing action '{EXECUTE_DEVICE_COMMAND_SCRIPT_NAME}'. Reason: {e}"
        status = EXECUTION_STATE_FAILED
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
        result_data = False

    return output_message, result_data, status


def query_operation_status(siemplify, manager, action_start_time, result_data, command):
    timeout_approaching = False
    is_timeout = is_async_action_global_timeout_approaching(
        siemplify, action_start_time
    )

    if is_timeout:
        siemplify.LOGGER.info("Timeout is approaching. Action will gracefully exit")
        timeout_approaching = True
    else:
        in_progress_items = result_data["in_progress"]

        for item in in_progress_items[:]:
            entity_identifier = item["entity"]
            device_id = item["device_id"]
            queue_items = item["queue_items"]

            for queue_item in queue_items[:]:
                q_item = manager.get_queue_data_single(
                    device_id=device_id, command_id=queue_item
                )

                if q_item.response is not None:
                    if not result_data["successful_entities"].get(entity_identifier):
                        result_data["successful_entities"][entity_identifier] = []
                    result_data["successful_entities"][entity_identifier].append(
                        q_item.as_json()
                    )
                    queue_items.remove(queue_item)

            # if still some items
            if queue_items:
                continue
            # if no more items for an entity
            else:
                in_progress_items.remove(item)
        if in_progress_items:
            output_message = (
                f"Waiting for commands execution to finish on the following entities: "
                f"{' '.join([item['entity'] for item in in_progress_items])}"
            )
            result_value = json.dumps(result_data)
            return output_message, result_value, EXECUTION_STATE_INPROGRESS

    output_message, result_value, status = finish_operation(
        siemplify=siemplify,
        result_data=result_data,
        timeout_approaching=timeout_approaching,
        command=command,
    )

    return output_message, result_value, status


def finish_operation(siemplify, result_data, timeout_approaching, command):
    output_message = ""
    result_value = True
    status = EXECUTION_STATE_COMPLETED
    successful_entities = []
    failed_entities = []
    in_progress_entities = []

    for entity in result_data["target_entities"]:
        if entity in result_data["successful_entities"]:
            successful_entities.append(entity)
        elif entity in result_data["failed_entities"]:
            failed_entities.append(entity)
        else:
            in_progress_entities.append(entity)

    if successful_entities:
        output_message = (
            f"Successfully executed command {command} on the following entities in Automox: "
            f'{", ".join(entity for entity in successful_entities)}\n'
            f"Please check the JSON result to be sure that the command executed correctly."
        )
        siemplify.LOGGER.info(output_message)
        siemplify.result.add_result_json(
            convert_dict_to_json_result_dict(result_data["successful_entities"])
        )

        if failed_entities:
            log_message = (
                f"Action wasn’t able to execute command {command} on the following entities in Automox: "
                f'{", ".join(entity for entity in failed_entities)}\n'
                f"Please check the spelling and connectivity."
            )
            output_message += log_message
            siemplify.LOGGER.info(log_message)

    if timeout_approaching and in_progress_entities:
        err = (
            f"Action ran into a timeout. Pending entities: "
            f"{', '.join(entity for entity in in_progress_entities)}\n"
            f"Please increase the timeout in IDE."
        )

        output_message = f"Error executing action {EXECUTE_DEVICE_COMMAND_SCRIPT_NAME}. Reason: {err}"
        siemplify.LOGGER.error(output_message)
        result_value = False
        status = EXECUTION_STATE_FAILED

        return output_message, result_value, status

    if not successful_entities:
        result_value = False
        output_message = "No commands were executed on the provided entities. Please check the spelling and connectivity."
        siemplify.LOGGER.info(output_message)

    return output_message, result_value, status


@output_handler
def main(is_first_run):
    siemplify = SiemplifyAction()
    siemplify.script_name = EXECUTE_DEVICE_COMMAND_SCRIPT_NAME
    action_start_time = unix_now()

    mode = "Main" if is_first_run else "QueryState"

    siemplify.LOGGER.info(f"----------------- {mode} - Param Init -----------------")

    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Root",
        print_value=True,
        is_mandatory=True,
    )
    api_key = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Key",
        remove_whitespaces=False,
        is_mandatory=True,
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        input_type=bool,
        is_mandatory=True,
        print_value=True,
    )

    command = extract_action_param(
        siemplify, param_name="Command", default_value="Scan Device", print_value=True
    )
    command = COMMANDS_MAPPER[command]

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    manager = AutomoxManager(api_root=api_root, api_key=api_key, verify_ssl=verify_ssl)

    try:
        if is_first_run:
            output_message, result_value, status = start_operation(
                siemplify, manager, command
            )
        else:
            result_data_json = extract_action_param(
                siemplify=siemplify,
                param_name="additional_data",
                default_value="{}",
                is_mandatory=True,
            )
            result_data = json.loads(result_data_json)

            output_message, result_value, status = query_operation_status(
                siemplify, manager, action_start_time, result_data, command
            )

    except Exception as e:
        output_message = f"Error executing action '{EXECUTE_DEVICE_COMMAND_SCRIPT_NAME}'. Reason: {e}"
        status = EXECUTION_STATE_FAILED
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
        result_value = False

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}"
        f"\n  is_success: {result_value}"
        f"\n  output_message: {output_message}"
    )
    siemplify.end(output_message, result_value, status)


def is_async_action_global_timeout_approaching(siemplify, start_time):
    return siemplify.execution_deadline_unix_time_ms - start_time < 1 * 60 * 1000


if __name__ == "__main__":
    is_first_run = len(sys.argv) < 3 or sys.argv[2] == "True"
    main(is_first_run)
