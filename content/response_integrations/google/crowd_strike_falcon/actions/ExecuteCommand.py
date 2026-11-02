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
from soar_sdk.SiemplifyUtils import output_handler, convert_dict_to_json_result_dict
from soar_sdk.ScriptResult import (
    EXECUTION_STATE_COMPLETED,
    EXECUTION_STATE_FAILED,
    EXECUTION_STATE_INPROGRESS,
)

from TIPCommon.extraction import extract_configuration_param, extract_action_param
from TIPCommon.validation import ParameterValidator

from crowd_strike_falcon.core.constants import (
    API_ROOT_DEFAULT,
    EXECUTE_COMMAND_SCRIPT_NAME,
    INTEGRATION_NAME,
    PRODUCT_NAME,
    STATUS_NORMAL,
    STATE_ONLINE,
    ENTITIES_MAPPER,
    CID_ERROR,
    STATE_OFFLINE,
)
from crowd_strike_falcon.core.CrowdStrikeManager import CrowdStrikeManager
from crowd_strike_falcon.core.exceptions import (
    CrowdStrikeError,
    CrowdStrikeSessionCreatedError,
    NoSuitableEntitiesException,
)
from crowd_strike_falcon.core.utils import get_entity_original_identifier, validate_device_id


def start_operation(
    siemplify,
    manager,
    command,
    admin_command,
    suitable_items_mapping,
    queue_offline,
    cid=None,
):
    (
        command_not_available_entities,
        not_found_entities,
        data_not_available_entities,
        not_accessible_entities,
        offline_entities,
        successful_entities,
    ) = ([], [], [], [], [], [])

    output_message = ""
    status = EXECUTION_STATE_INPROGRESS
    seen_devices = {}
    result_value = {
        "in_progress": {},
        "completed": {},
        "command_not_available": [],
        "data_not_available": [],
        "not_found": [],
        "not_accessible_entities": [],
        "offline_queued": [],
    }
    for entity_identifier, entity_type in suitable_items_mapping.items():
        if entity_type == "DEVICE_ID":
            devices = [entity_identifier]
        else:
            request_filter = {
                key: entity_identifier for key in ENTITIES_MAPPER.get(entity_type, [])
            }
            request_filter["cid"] = cid
            devices = manager.search_device_ids(**request_filter)

        if not devices:
            not_found_entities.append(entity_identifier)
            result_value["not_found"].append(entity_identifier)
            continue

        if len(devices) > 1:
            siemplify.LOGGER.info(
                f"Multiple entries were found for entity: {entity_identifier}. "
                f"First online will be used"
            )

        try:
            devices_info = manager.get_devices(devices_ids=devices)
            online_state = manager.get_devices_online_states(devices)

            for device_info in devices_info:
                device_info.online_state = next(
                    (
                        state
                        for state in online_state
                        if state.device_id == device_info.device_id
                    ),
                    None,
                )

            online_device = next(
                (
                    device
                    for device in devices_info
                    if device.status == STATUS_NORMAL
                    and device.online_state
                    and device.online_state.state == STATE_ONLINE
                ),
                None,
            )

            if not online_device:
                offline_device = next(
                    (
                        device
                        for device in devices_info
                        if device.status == STATUS_NORMAL
                        and device.online_state
                        and device.online_state.state == STATE_OFFLINE
                    ),
                    None,
                )
                if offline_device and queue_offline:
                    if offline_device.device_id in seen_devices:
                        siemplify.LOGGER.info(
                            f"Identifier '{entity_identifier}' maps to device ID "
                            f"'{offline_device.device_id}', which is already "
                            f"associated with entity '{seen_devices[offline_device.device_id]}'. "
                            "Skipping duplication."
                        )
                        continue
                    seen_devices[offline_device.device_id] = entity_identifier

                    offline_entities.append(entity_identifier)
                    session_id = manager.create_device_session(
                        device_id=offline_device.device_id
                    )
                    if not session_id:
                        data_not_available_entities.append(entity_identifier)
                        result_value["data_not_available"].append(entity_identifier)
                        offline_entities.remove(entity_identifier)
                        continue

                    try:
                        cloud_request_id = manager.execute_responder_command(
                            session_id=session_id,
                            command=command,
                            admin_command=admin_command,
                            device_id=offline_device.device_id,
                        )
                        result_value["offline_queued"].append({
                            "entity_identifier": entity_identifier,
                            "api_response": {
                                "session_id": session_id,
                                "cloud_request_id": cloud_request_id,
                                "queued_command_offline": True
                            }
                        })
                    except CrowdStrikeError:
                        command_not_available_entities.append(entity_identifier)
                        offline_entities.remove(entity_identifier)
                else:
                    not_accessible_entities.append(entity_identifier)
                    result_value["not_accessible_entities"].append(entity_identifier)

                continue

            if online_device.device_id in seen_devices:
                siemplify.LOGGER.info(
                    f"Identifier '{entity_identifier}' maps to device ID "
                    f"'{online_device.device_id}', which is already "
                    f"associated with entity '{seen_devices[online_device.device_id]}'. "
                    "Skipping duplication."
                )
                continue
            seen_devices[online_device.device_id] = entity_identifier

            session_id = manager.create_device_session(
                device_id=online_device.device_id
            )
            if not session_id:
                data_not_available_entities.append(entity_identifier)
                result_value["data_not_available"].append(entity_identifier)
                continue

            cloud_request_id = manager.execute_responder_command(
                session_id=session_id,
                command=command,
                admin_command=admin_command,
                device_id=online_device.device_id,
            )
            if not cloud_request_id:
                command_not_available_entities.append(entity_identifier)
                result_value["command_not_available"].append(entity_identifier)
                continue

            result_value["in_progress"][entity_identifier] = cloud_request_id
            successful_entities.append(entity_identifier)
        except CrowdStrikeSessionCreatedError as e:
            data_not_available_entities.append(entity_identifier)
            result_value["data_not_available"].append(entity_identifier)
            siemplify.LOGGER.error(f"An error occurred on entity {entity_identifier}")
            siemplify.LOGGER.exception(e)

        except Exception as e:
            command_not_available_entities.append(entity_identifier)
            result_value["command_not_available"].append(entity_identifier)
            siemplify.LOGGER.error(f"An error occurred on entity {entity_identifier}")
            siemplify.LOGGER.exception(e)

    if successful_entities:
        output_message = (
            f"Successfully created sessions for the following endpoints in {PRODUCT_NAME}: "
            f'{", ".join(successful_entities)}\n'
        )
        result_value = json.dumps(result_value)

        if data_not_available_entities:
            output_message += (
                f"Action wasn't able to created sessions for the following endpoints in "
                f'{PRODUCT_NAME}: {", ".join(data_not_available_entities)}\n'
            )
        if not_accessible_entities:
            output_message += (
                f"Action wasn't able to execute command on the following machines: "
                f'{", ".join(not_accessible_entities)}. Reason: machines are not '
                f"accessible. Please validate the connection.\n"
            )
        if offline_entities:
            output_message += (
                "Command has been queued for the following offline endpoints in "
                f"{PRODUCT_NAME}: "
                f'{", ".join(offline_entities)}\n'
            )
    elif offline_entities and not successful_entities:
        output_message += (
            "Command has been queued for the following offline endpoints in "
            f"{PRODUCT_NAME}: {', '.join(offline_entities)}\n"
        )
        if result_value["not_found"]:
            output_message += (
                f"The following endpoints were not found in {PRODUCT_NAME}: "
                f'{", ".join(result_value["not_found"])}\n'
            )
        status = EXECUTION_STATE_COMPLETED
        json_results = {}
        for item in result_value.get("offline_queued", []):
            json_results[item["entity_identifier"]] = item["api_response"]

        result_value = True
        if json_results:
            siemplify.result.add_result_json(
                convert_dict_to_json_result_dict(json_results)
                )


    else:
        if (
            command_not_available_entities
            and not not_found_entities
            and not data_not_available_entities
            and not not_accessible_entities
            and not offline_entities
        ):
            output_message = (
                f"Command '{command}' was not found on the provided endpoints in "
                f"{PRODUCT_NAME}."
            )

        elif (
            not_found_entities
            and not command_not_available_entities
            and not data_not_available_entities
            and not not_accessible_entities
        ):
            output_message = (
                f"None of the provided endpoints were found in {PRODUCT_NAME}."
            )

        elif (
            data_not_available_entities
            and not command_not_available_entities
            and not not_found_entities
            and not not_accessible_entities
        ):
            output_message = (
                f"Command '{command}' wasn't executed on the provided endpoints in "
                f"{PRODUCT_NAME}.\n"
            )
        elif (
            not_accessible_entities
            and not data_not_available_entities
            and not command_not_available_entities
            and not not_found_entities
        ):
            output_message = (
                f"Action wasn't able to execute command on the provided machines. Reason: machines are "
                f"not accessible. Please validate the connection.\n"
            )
        else:
            if command_not_available_entities:
                output_message += (
                    f"Command '{command}' was not found on the following endpoints in "
                    f"{PRODUCT_NAME}: {', '.join(command_not_available_entities)}\n"
                )
            if not_found_entities:
                output_message += (
                    f"The following endpoints were not found in "
                    f"{PRODUCT_NAME}: {', '.join(not_found_entities)}\n"
                )
            if data_not_available_entities:
                output_message += (
                    f"Action wasn't able to execute command '{command}' on the following endpoints in "
                    f"{PRODUCT_NAME}: {', '.join(data_not_available_entities)}\n"
                )
            if not_accessible_entities:
                output_message += (
                    f"Action wasn't able to execute command on the following machines: "
                    f"{', '.join(not_accessible_entities)}. Reason: machines are not "
                    f"accessible. Please validate the connection.\n"
                )

        result_value = False
        status = EXECUTION_STATE_COMPLETED

    return output_message, result_value, status


def query_operation_status(
    siemplify,
    manager,
    sessions,
    admin_command,
    suitable_items_mapping,
    command_to_execute
):
    completed_entities = {}
    for entity, cloud_request_id in sessions["in_progress"].items():
        try:
            commands = manager.get_status_of_responder_command(
                cloud_request_id=cloud_request_id, admin_command=admin_command
            )
            for single_command in commands:
                if single_command.complete:
                    completed_entities[entity] = single_command.to_json()
        except CrowdStrikeSessionCreatedError as e:
            sessions["data_not_available"].append(entity)
            siemplify.LOGGER.error(f"An error occurred on entity {entity}")
            siemplify.LOGGER.exception(e)

        except Exception as e:
            sessions["command_not_available"].append(entity)
            siemplify.LOGGER.error(f"An error occurred on entity {entity}")
            siemplify.LOGGER.exception(e)

    for key in completed_entities.keys():
        sessions["in_progress"].pop(key)
    for failed_entity in sessions["command_not_available"]:
        if failed_entity in sessions["in_progress"].keys():
            sessions["in_progress"].pop(failed_entity)
    for failed_entity in sessions["data_not_available"]:
        if failed_entity in sessions["in_progress"].keys():
            sessions["in_progress"].pop(failed_entity)
    sessions["completed"].update(completed_entities)

    if sessions["in_progress"]:
        status = EXECUTION_STATE_INPROGRESS
        result_value = json.dumps(sessions)
        output_message = f"Waiting for results for the following entities: {', '.join(sessions['in_progress'].keys())}"
    else:
        output_message, result_value, status = finish_operation(
            siemplify=siemplify,
            command=command_to_execute,
            suitable_items_mapping=suitable_items_mapping,
            completed_entities=sessions["completed"],
            command_not_available_entities=sessions["command_not_available"],
            not_found_entities=sessions["not_found"],
            data_not_available_entities=sessions["data_not_available"],
            not_accessible_entities=sessions["not_accessible_entities"],
            offline_entities=sessions.get("offline_queued", []),
        )

    return output_message, result_value, status


def finish_operation(
    siemplify,
    command,
    suitable_items_mapping,
    completed_entities,
    command_not_available_entities,
    not_found_entities,
    data_not_available_entities,
    not_accessible_entities,
    offline_entities,
):
    result_value = True
    output_message = ""
    status = EXECUTION_STATE_COMPLETED
    successful_entities, json_results = [], {}

    for entity_identifier, _ in suitable_items_mapping.items():
        if entity_identifier in completed_entities.keys():
            entity_result = completed_entities[entity_identifier]
            json_results[entity_identifier] = entity_result

            successful_entities.append(entity_identifier)

    for offline_item in offline_entities:
        entity_identifier = offline_item.get("entity_identifier")
        if entity_identifier:
            json_results[entity_identifier] = offline_item.get("api_response")

    if successful_entities:
        output_message += (
            f"Successfully executed command '{command}' on the following endpoints in {PRODUCT_NAME}: "
            f"{', '.join(successful_entities)}\n"
        )
    if command_not_available_entities:
        output_message += (
            f"Command '{command}' was not found on the following endpoints in "
            f"{PRODUCT_NAME}: {', '.join(command_not_available_entities)}\n"
        )
    if not_found_entities:
        output_message += (
            f"The following endpoints were not found in "
            f"{PRODUCT_NAME}: {', '.join(not_found_entities)}\n"
        )
    if data_not_available_entities:
        output_message += (
            f"Action wasn't able to execute command '{command}' on the following endpoints in "
            f"{PRODUCT_NAME}: {', '.join(data_not_available_entities)}\n"
        )
    if not_accessible_entities:
        output_message += (
            f"Action wasn't able to execute command on the following machines: "
            f"{', '.join(not_accessible_entities)}. "
            "Reason: machines are not accessible. "
            f"Please validate the connection.\n"
        )
    if offline_entities:
        output_message += (
            "Command has been queued for the following offline endpoints in "
            f"{PRODUCT_NAME}: " +
            ", ".join([
                item.get("entity_identifier") for item in offline_entities
                if item.get("entity_identifier")
            ]) + "\n"
        )

    if not successful_entities:
        result_value = False

        if (
            command_not_available_entities
            and not not_found_entities
            and not data_not_available_entities
            and not not_accessible_entities
        ):
            output_message = (
                f"Command '{command}' was not found on the provided endpoints in "
                f"{PRODUCT_NAME}.\n"
            )
        elif (
            data_not_available_entities
            and not not_found_entities
            and not command_not_available_entities
            and not not_accessible_entities
        ):
            output_message = (
                f"Command '{command}' wasn't executed on the provided endpoints in "
                f"{PRODUCT_NAME}.\n"
            )
        elif (
            not_found_entities
            and not command_not_available_entities
            and not data_not_available_entities
            and not not_accessible_entities
        ):
            output_message = (
                f"None of the provided endpoints were found in {PRODUCT_NAME}.\n"
            )

        elif (
            not_accessible_entities
            and not data_not_available_entities
            and not command_not_available_entities
            and not not_found_entities
        ):
            output_message = (
                f"Action wasn't able to execute command on the provided machines. Reason: machines are "
                f"not accessible. Please validate the connection.\n"
            )

    if json_results:
        siemplify.result.add_result_json(convert_dict_to_json_result_dict(json_results))

    return output_message, result_value, status


@output_handler
def main(is_first_run):
    siemplify = SiemplifyAction()
    siemplify.script_name = EXECUTE_COMMAND_SCRIPT_NAME
    mode = "Main" if is_first_run else "Get Report"

    siemplify.LOGGER.info(f"----------------- {mode} - Param Init -----------------")

    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Root",
        default_value=API_ROOT_DEFAULT,
    )
    client_id = extract_configuration_param(
        siemplify, provider_name=INTEGRATION_NAME, param_name="Client API ID"
    )
    client_secret = extract_configuration_param(
        siemplify, provider_name=INTEGRATION_NAME, param_name="Client API Secret"
    )
    use_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        input_type=bool,
        is_mandatory=True,
    )

    integration_cid = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Customer ID",
        print_value=True
    )
    action_cid = extract_action_param(
        siemplify,
        param_name="Customer ID",
        print_value=True,
    )
    customer_id = action_cid or integration_cid
    command_to_execute = extract_action_param(
        siemplify, param_name="Command", is_mandatory=True, print_value=True
    )
    admin_command = extract_action_param(
        siemplify,
        param_name="Admin Command",
        input_type=bool,
        is_mandatory=False,
        print_value=True,
    )
    hostname = extract_action_param(
        siemplify,
        param_name="Hostname",
        is_mandatory=False,
        print_value=True,
    )
    device_id_param = extract_action_param(
        siemplify,
        param_name="Device ID",
        print_value=True,
    )
    queue_offline = extract_action_param(
        siemplify,
        param_name="Queue Offline",
        input_type=bool,
        print_value=True,
        default_value=False,
    )
    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    status = EXECUTION_STATE_INPROGRESS
    result_value = False
    output_message = ""
    suitable_entities = [
        entity
        for entity in siemplify.target_entities
        if entity.entity_type in ENTITIES_MAPPER
    ]


    try:
        validate_device_id(device_id_param)
        validator = ParameterValidator(siemplify)

        hostnames = validator.validate_csv(
            param_name="Hostname",
            csv_string=hostname,
        )
        device_ids = validator.validate_csv(
            param_name="Device ID",
            csv_string=device_id_param,
        )

        if not suitable_entities and not hostnames and not device_ids:
            raise NoSuitableEntitiesException

        suitable_items_mapping = {
            get_entity_original_identifier(entity): entity.entity_type
            for entity in suitable_entities
        }

        suitable_items_mapping.update({
            hostname: EntityTypes.HOSTNAME
            for hostname in hostnames
        })
        suitable_items_mapping.update({
            device_id: "DEVICE_ID"
            for device_id in device_ids
        })

        manager = CrowdStrikeManager(
            client_id=client_id,
            client_secret=client_secret,
            use_ssl=use_ssl,
            api_root=api_root,
            force_check_connectivity=True,
            customer_id=customer_id,
        )

        if is_first_run:
            output_message, result_value, status = start_operation(
                siemplify,
                manager=manager,
                command=command_to_execute,
                admin_command=admin_command,
                suitable_items_mapping=suitable_items_mapping,
                queue_offline=queue_offline,
                cid=customer_id,
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
                sessions=json.loads(sessions),
                admin_command=admin_command,
                suitable_items_mapping=suitable_items_mapping,
                command_to_execute=command_to_execute,
            )

    except NoSuitableEntitiesException:
        output_message = (
            "Action didn't execute any commands. None of the entities are of type "
            "Hostname or IP Address, and no value provided in the \"Hostname\" or \"Device ID\" "
            "parameter."
        )
        status = EXECUTION_STATE_COMPLETED
    except Exception as e:
        error_message = f"Error executing action {EXECUTE_COMMAND_SCRIPT_NAME}."
        output_message = f"{error_message} Reason: {e}"

        if CID_ERROR in str(e).lower():
            output_message = f"{error_message} Reason: Incorrect Customer ID specified."

        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        result_value = False

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  is_success: {result_value}\n  output_message: {output_message}"
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    is_first_run = len(sys.argv) < 3 or sys.argv[2] == "True"
    main(is_first_run)
