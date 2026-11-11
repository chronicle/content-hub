from __future__ import annotations
import json
import sys
from tanium.core import constants
from time import sleep
from tanium.core.TaniumManager import TaniumManager
from soar_sdk.ScriptResult import (
    EXECUTION_STATE_COMPLETED,
    EXECUTION_STATE_FAILED,
    EXECUTION_STATE_INPROGRESS,
)
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyUtils import output_handler, unix_now, convert_dict_to_json_result_dict
from TIPCommon import extract_configuration_param, extract_action_param
from tanium.core.constants import (
    INTEGRATION_NAME,
    QUARANTINE_ENDPOINT_SCRIPT_NAME,
    TASK_STATUS_COMPLETED,
    TASK_STATUS_INCOMPLETE,
    TASK_STATUS_ERROR,
    DEFAULT_TIMEOUT,
    CONNECTED_STATUS,
    QUARANTINE_TASK,
)
from tanium.core.utils import (
    get_entity_original_identifier,
    is_async_action_global_timeout_approaching,
    is_approaching_process_timeout,
    unixtime_to_rfc3339,
)
from tanium.core.exceptions import InvalidJsonException

SUPPORTED_ENTITIES = [EntityTypes.ADDRESS, EntityTypes.HOSTNAME]


def start_operation(
    siemplify, manager, suitable_entities, only_initiate, package_names, package_params
):
    """Initiating the tasks for given entities."""
    result_value = {"to_process": {}, "completed": {}, "not_found": [], "failed": {}}
    status = EXECUTION_STATE_INPROGRESS
    open_connections = manager.get_open_connections()
    siemplify.LOGGER.info(
        f"open connections - {[(conn.id, conn.status) for conn in open_connections]}"
    )
    siemplify.LOGGER.info(
        f"suitable entities - {[entity.identifier for entity in suitable_entities]}"
    )
    for entity in suitable_entities:
        entity_identifier = get_entity_original_identifier(entity)
        siemplify.LOGGER.info(f"Started processing entity: {entity_identifier}")
        try:
            entity_connections = [
                connection
                for connection in open_connections
                if entity_identifier in [connection.ip, connection.hostname]
            ]
            siemplify.LOGGER.info(
                f"entity connections - "
                f"{[(conn.id, conn.status) for conn in entity_connections]}"
            )
            if entity_connections:
                enabled_connection = next(
                    (
                        connection
                        for connection in entity_connections
                        if connection.status == CONNECTED_STATUS
                    ),
                    None,
                )
                siemplify.LOGGER.info(f"Found connection for {entity.identifier}")
                if not enabled_connection:
                    siemplify.LOGGER.info("Disabled. Creating connection... ")
                    manager.create_conection(
                        hostname=entity_connections[0].hostname,
                        ip=entity_connections[0].ip,
                        client_id=entity_connections[0].client_id,
                        platform=entity_connections[0].platform,
                    )
                    for i in range(3):
                        siemplify.LOGGER.info("Checking connection status... ")
                        sleep(5)
                        open_connections = manager.get_open_connections()
                        entity_connections = [
                            connection
                            for connection in open_connections
                            if entity_identifier in [connection.ip, connection.hostname]
                        ]
                        enabled_connection = next(
                            (
                                connection
                                for connection in entity_connections
                                if connection.status == CONNECTED_STATUS
                            ),
                            None,
                        )
                        if enabled_connection:
                            break
                    if not enabled_connection:
                        siemplify.LOGGER.info(
                            f"Connection was not enabled. Skipping entity {entity_identifier}."
                        )
                        result_value["not_found"].append(entity_identifier)
                        continue
                siemplify.LOGGER.info("Initiating quarantine task.")
                task_id = manager.initiate_quarantine(
                    computer_name=enabled_connection.hostname,
                    package_name=package_names.get(enabled_connection.platform),
                    expiration_time=unixtime_to_rfc3339(
                        siemplify.execution_deadline_unix_time_ms
                    ),
                    package_params=package_params,
                )
                siemplify.LOGGER.info(f"Initialized quarantine task id - {task_id}")
                sleep(5)
                tasks = manager.get_tasks()
                quarantine_task = next(
                    (
                        task
                        for task in tasks
                        if task.meta_type == QUARANTINE_TASK and task.meta_id == task_id
                    ),
                    None,
                )
                if only_initiate:
                    result_value["completed"][
                        entity_identifier
                    ] = quarantine_task.to_json()
                else:
                    if quarantine_task.status not in [
                        TASK_STATUS_COMPLETED,
                        TASK_STATUS_INCOMPLETE,
                        TASK_STATUS_ERROR,
                    ]:
                        result_value["to_process"][
                            entity_identifier
                        ] = quarantine_task.id
                    elif quarantine_task.status == TASK_STATUS_COMPLETED:
                        result_value["completed"][
                            entity_identifier
                        ] = quarantine_task.to_json()
                    else:
                        result_value["failed"][
                            entity_identifier
                        ] = quarantine_task.to_json()
            else:
                siemplify.LOGGER.info(f"No connection found for {entity.identifier}")
                result_value["not_found"].append(entity_identifier)
        except Exception as err:
            result_value["not_found"].append(entity_identifier)
            siemplify.LOGGER.error(f"An error occurred on entity {entity_identifier}")
            siemplify.LOGGER.exception(err)
        siemplify.LOGGER.info(f"Finished processing entity: {entity_identifier}")

    if result_value["to_process"] and not only_initiate:
        output_message = "Pending entities: " "{}".format(
            ", ".join([key for key, value in result_value["to_process"].items()])
        )
        result_value = json.dumps(result_value)
        return output_message, result_value, status

    output_message, result_value, status = finish_operation(
        siemplify=siemplify,
        suitable_entities=suitable_entities,
        result_data=result_value,
        timeout_approaching=False,
    )

    return output_message, result_value, status


def query_operation_status(
    siemplify, manager, action_start_time, result_data, suitable_entities
):
    timeout_approaching = False

    for entity_identifier, task_id in result_data["to_process"].items():
        try:
            if is_async_action_global_timeout_approaching(
                siemplify, action_start_time
            ) or is_approaching_process_timeout(action_start_time, DEFAULT_TIMEOUT):
                siemplify.LOGGER.info(
                    "Timeout is approaching. Action will gracefully exit"
                )
                timeout_approaching = True
                break
            task = manager.get_task_details(task_id=task_id)
            if task.status not in [
                TASK_STATUS_COMPLETED,
                TASK_STATUS_INCOMPLETE,
                TASK_STATUS_ERROR,
            ]:
                continue
            elif task.status == TASK_STATUS_COMPLETED:
                result_data["completed"][entity_identifier] = task.to_json()
            else:
                result_data["failed"][entity_identifier] = task.to_json()
        except Exception as err:
            result_data["not_found"].append(entity_identifier)
            siemplify.LOGGER.error(f"An error occurred on entity {entity_identifier}")
            siemplify.LOGGER.exception(err)

    for key in (
        list(result_data["completed"].keys())
        + list(result_data["failed"].keys())
        + result_data["not_found"]
    ):
        result_data["to_process"].pop(key, None)

    if result_data["to_process"] and not timeout_approaching:
        output_message = "Pending entities: " "{}".format(
            ", ".join([key for key, value in result_data["to_process"].items()])
        )
        result_value = json.dumps(result_data)
        return output_message, result_value, EXECUTION_STATE_INPROGRESS

    output_message, result_value, status = finish_operation(
        siemplify=siemplify,
        suitable_entities=suitable_entities,
        result_data=result_data,
        timeout_approaching=timeout_approaching,
    )

    return output_message, result_value, status


def finish_operation(siemplify, suitable_entities, result_data, timeout_approaching):
    result_value = True
    status = EXECUTION_STATE_COMPLETED
    not_found_entities = result_data["not_found"]
    successful_entities, failed_entities, pending_entities = [], [], []
    json_results = {}
    output_message = ""

    for entity in suitable_entities:
        entity_identifier = get_entity_original_identifier(entity)
        if entity_identifier in result_data["completed"].keys():
            successful_entities.append(entity_identifier)
        if entity_identifier in result_data["failed"].keys():
            failed_entities.append(entity_identifier)
        if entity_identifier in result_data["to_process"].keys():
            pending_entities.append(entity_identifier)

    if timeout_approaching and pending_entities:
        raise Exception(
            f"action ran into a timeout during execution. Pending entities: {', '.join(pending_entities)}. "
            f'Please increase the timeout in IDE or enable "Only Initiate".\n'
        )

    if successful_entities:
        output_message += (
            f"Successfully initiated quarantine on the following endpoints in {INTEGRATION_NAME}: "
            f"{', '.join(successful_entities)}. \n\n"
        )
    if failed_entities:
        output_message += (
            f"Action wasn't able to quarantine the following endpoints in {INTEGRATION_NAME}: "
            f"{', '.join(failed_entities)}.\nPlease make sure that the Tanium Threat Response agent "
            f"is connected properly and the hostname/IP address is correct.\n\n"
        )
    if not_found_entities:
        output_message += (
            f"Action wasn't able to create tasks on the following endpoints in {INTEGRATION_NAME}: "
            f"{', '.join(not_found_entities)}.\nPlease make sure that the Tanium Threat Response agent "
            f"is connected properly and the hostname/IP address is correct.\n\n"
        )
    if not successful_entities:
        result_value = False
        if not failed_entities and not not_found_entities:
            output_message = "No suitable entities were found in the scope."
        elif not failed_entities and not_found_entities:
            raise Exception(
                "action wasn't able to quarantine the provided endpoints in Tanium due to agent "
                "connectivity issues. Please make sure that the endpoints are connected to the Tanium "
                "Threat Response module and the hostname/IP address is correct."
            )
        elif failed_entities and not not_found_entities:
            output_message = (
                "Action wasn't able to quarantine the provided endpoints in Tanium. Please make sure "
                "that the Tanium Threat Response agent is connected properly and the hostname/IP "
                "address is correct."
            )

    if successful_entities or failed_entities:
        for identifier, task_details in result_data["completed"].items():
            json_results[identifier] = task_details
        for identifier, task_details in result_data["failed"].items():
            json_results[identifier] = task_details
        siemplify.result.add_result_json(convert_dict_to_json_result_dict(json_results))

    return output_message, result_value, status


@output_handler
def main(is_first_run):
    siemplify = SiemplifyAction()
    action_start_time = unix_now()
    siemplify.script_name = QUARANTINE_ENDPOINT_SCRIPT_NAME
    mode = "Main" if is_first_run else "Quarantine Endpoint"
    siemplify.LOGGER.info(f"----------------- {mode} - Param Init -----------------")

    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Root",
        is_mandatory=True,
        print_value=True,
    )
    api_token = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Token",
        is_mandatory=True,
        remove_whitespaces=False,
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        input_type=bool,
        print_value=True,
    )

    # Action parameters
    only_initiate = extract_action_param(
        siemplify,
        param_name="Only Initiate",
        is_mandatory=False,
        default_value=False,
        input_type=bool,
    )
    package_names = extract_action_param(
        siemplify, param_name="Package Names", print_value=True, is_mandatory=True
    )

    package_params = extract_action_param(
        siemplify, param_name="Package Parameters", print_value=True
    )

    siemplify.LOGGER.info(f"----------------- {mode} - Started -----------------")

    result_value = False
    suitable_entities = [
        entity
        for entity in siemplify.target_entities
        if entity.entity_type in SUPPORTED_ENTITIES
    ]

    try:
        try:
            package_names = json.loads(package_names)
        except Exception as e:
            raise InvalidJsonException(
                'Invalid JSON provided in the parameter "Package Names". '
                "Please check the structure."
            ) from e

        if package_params:
            try:
                package_params = json.loads(package_params)
            except Exception as e:
                raise InvalidJsonException(
                    'Invalid JSON provided in the parameter "Package Parameters". '
                    "Please check the structure."
                ) from e

        manager = TaniumManager(
            api_root=api_root,
            api_token=api_token,
            verify_ssl=verify_ssl,
            force_check_connectivity=True,
            logger=siemplify.LOGGER,
        )

        if is_first_run:
            output_message, result_value, status = start_operation(
                siemplify=siemplify,
                manager=manager,
                suitable_entities=suitable_entities,
                only_initiate=only_initiate,
                package_names=package_names,
                package_params=package_params or constants.PACKAGE_PARAMETERS,
            )
        else:
            result_data = (
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
                result_data=json.loads(result_data),
                suitable_entities=suitable_entities,
            )

    except Exception as err:
        output_message = (
            f"Error executing action {QUARANTINE_ENDPOINT_SCRIPT_NAME}. Reason: {err}"
        )
        result_value = False
        status = EXECUTION_STATE_FAILED
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(err)

    siemplify.LOGGER.info(f"----------------- {mode} - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  is_success: {result_value}\n  output_message: {output_message}"
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    is_first_run = len(sys.argv) < 3 or sys.argv[2] == "True"
    main(is_first_run)
