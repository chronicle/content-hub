from __future__ import annotations
import json
import sys
import os
from time import sleep
from tanium.core.TaniumManager import TaniumManager
from soar_sdk.ScriptResult import (
    EXECUTION_STATE_COMPLETED,
    EXECUTION_STATE_FAILED,
    EXECUTION_STATE_INPROGRESS,
)
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyUtils import output_handler, unix_now
from TIPCommon import extract_configuration_param, extract_action_param
from tanium.core.constants import (
    INTEGRATION_NAME,
    DOWNLOAD_FILE_SCRIPT_NAME,
    TASK_STATUS_COMPLETED,
    TASK_STATUS_INCOMPLETE,
    TASK_STATUS_ERROR,
    DEFAULT_TIMEOUT,
    CONNECTED_STATUS,
)
from tanium.core.exceptions import FileExistsException
from tanium.core.utils import (
    get_entity_original_identifier,
    is_async_action_global_timeout_approaching,
    is_approaching_process_timeout,
    convert_comma_separated_to_list,
    save_attachment,
)

SUPPORTED_ENTITIES = [EntityTypes.ADDRESS, EntityTypes.HOSTNAME]


def start_operation(
    siemplify, manager, suitable_entities, file_paths, download_folder_path, overwrite
):
    result_value = {
        "to_process": {},
        "completed": {},
        "not_found": [],
        "failed": {},
        "absolute_paths": [],
    }
    status = EXECUTION_STATE_INPROGRESS
    open_connections = manager.get_open_connections()
    for entity in suitable_entities:
        entity_identifier = get_entity_original_identifier(entity)
        siemplify.LOGGER.info(f"Started processing entity: {entity_identifier}")
        try:
            entity_connections = [
                connection
                for connection in open_connections
                if entity_identifier in [connection.ip, connection.hostname]
            ]
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
                        result_value["not_found"].append(entity)
                        continue
                    connection_id = enabled_connection.id
                else:
                    connection_id = enabled_connection.id

                for file_path in file_paths:
                    task_id = manager.create_file_evidence_task(
                        connection_id, file_path
                    )
                    task = manager.get_task_details(task_id=task_id)
                    filename = f"{entity_identifier}_{task.file_uuid}_{os.path.basename(file_path)}"
                    absolute_file_path = f"{download_folder_path}{filename}"
                    if not overwrite:
                        if os.path.exists(absolute_file_path):
                            raise FileExistsException(
                                f'files with path {absolute_file_path} already exist. Please delete the files or set "Overwrite" to true.'
                            )
                    if task.status not in [
                        TASK_STATUS_COMPLETED,
                        TASK_STATUS_INCOMPLETE,
                        TASK_STATUS_ERROR,
                    ]:
                        if result_value["to_process"].get(entity_identifier):
                            result_value["to_process"][entity_identifier].append(
                                task.id
                            )
                        else:
                            result_value["to_process"][entity_identifier] = [task.id]
                    elif task.status == TASK_STATUS_COMPLETED:
                        file_content = manager.get_file(file_uuid=task.file_uuid)
                        save_attachment(
                            path=download_folder_path,
                            name=filename,
                            content=file_content,
                        )
                        result_value["absolute_paths"].append(absolute_file_path)
                        if result_value["completed"].get(entity_identifier):
                            result_value["completed"][entity_identifier].append(
                                task.to_json()
                            )
                        else:
                            result_value["completed"][entity_identifier] = [
                                task.to_json()
                            ]
                    else:
                        if result_value["failed"].get(entity_identifier):
                            result_value["failed"][entity_identifier].append(
                                task.to_json()
                            )
                        else:
                            result_value["failed"][entity_identifier] = [task.to_json()]
            else:
                siemplify.LOGGER.info(f"No connection found for {entity.identifier}")
                result_value["not_found"].append(entity_identifier)
        except FileExistsException as e:
            raise Exception(e)
        except Exception as err:
            result_value["not_found"].append(entity_identifier)
            siemplify.LOGGER.error(f"An error occurred on entity {entity_identifier}")
            siemplify.LOGGER.exception(err)

    if result_value["to_process"]:
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
    siemplify,
    manager,
    action_start_time,
    result_data,
    suitable_entities,
    download_folder_path,
    overwrite,
):
    timeout_approaching = False

    for entity_identifier, task_ids in result_data["to_process"].items():
        if is_async_action_global_timeout_approaching(
            siemplify, action_start_time
        ) or is_approaching_process_timeout(action_start_time, DEFAULT_TIMEOUT):
            siemplify.LOGGER.info("Timeout is approaching. Action will gracefully exit")
            timeout_approaching = True
            break
        for task_id in task_ids:
            try:
                task = manager.get_task_details(task_id=task_id)
                filename = f"{entity_identifier}_{task.file_uuid}_{os.path.basename(task.file_path)}"
                absolute_file_path = f"{download_folder_path}{filename}"
                if not overwrite:
                    if os.path.exists(absolute_file_path):
                        raise FileExistsException(
                            f'files with path {absolute_file_path} already exist. Please delete the files or set "Overwrite" to true.'
                        )
                if task.status not in [
                    TASK_STATUS_COMPLETED,
                    TASK_STATUS_INCOMPLETE,
                    TASK_STATUS_ERROR,
                ]:
                    continue
                elif task.status == TASK_STATUS_COMPLETED:
                    file_content = manager.get_file(file_uuid=task.file_uuid)
                    save_attachment(
                        path=download_folder_path, name=filename, content=file_content
                    )
                    result_data["absolute_paths"].append(absolute_file_path)
                    if result_data["completed"].get(entity_identifier):
                        result_data["completed"][entity_identifier].append(
                            task.to_json()
                        )
                    else:
                        result_data["completed"][entity_identifier] = [task.to_json()]
                else:
                    if result_data["failed"].get(entity_identifier):
                        result_data["failed"][entity_identifier].append(task.to_json())
                    else:
                        result_data["failed"][entity_identifier] = [task.to_json()]

            except FileExistsException as e:
                raise Exception(e)
            except Exception as err:
                result_data["not_found"].append(entity_identifier)
                siemplify.LOGGER.error(
                    f"An error occurred on entity {entity_identifier}"
                )
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
    output_message = ""

    for entity in suitable_entities:
        entity_identifier = get_entity_original_identifier(entity)
        if entity_identifier in result_data["completed"].keys():
            successful_entities.append(entity_identifier)
        if entity_identifier in result_data["failed"].keys():
            failed_entities.append(entity_identifier)
        if entity_identifier in result_data["to_process"].keys():
            pending_entities.append(entity_identifier)
    if successful_entities:
        for identifier in successful_entities:
            entity_details = next(
                (
                    details
                    for entity, details in result_data["completed"].items()
                    if entity == identifier
                ),
                None,
            )
            successful_files = [
                detail.get("metadata", {}).get("paths")[0] for detail in entity_details
            ]
            output_message += (
                f"Successfully downloaded the following files from the endpoint {identifier} in {INTEGRATION_NAME}: "
                f"{', '.join(successful_files)}. \n\n"
            )
    if failed_entities:
        for identifier in failed_entities:
            entity_details = next(
                (
                    details
                    for entity, details in result_data["failed"].items()
                    if entity == identifier
                ),
                None,
            )
            failed_files = [
                detail.get("metadata", {}).get("paths")[0] for detail in entity_details
            ]
            output_message += (
                f"Action wasn't able to download the following files from the endpoint {identifier} in {INTEGRATION_NAME}: "
                f"{', '.join(failed_files)}.\nPlease make sure that the Tanium Threat Response agent "
                f"is connected properly and the hostname/IP address is correct. The JSON result has more "
                f"details about the tasks.\n\n"
            )
    if not_found_entities:
        output_message += (
            f"Action wasn't able to create tasks on the following endpoints in {INTEGRATION_NAME}: "
            f"{', '.join(not_found_entities)}.\nPlease make sure that the Tanium Threat Response agent "
            f"is connected properly and the hostname/IP address is correct.\n\n"
        )
    if not successful_entities:
        if not failed_entities and not not_found_entities:
            output_message = "No suitable entities were found in the scope."
        elif failed_entities and not not_found_entities:
            output_message = (
                "Action wasn't able to download files from the provided endpoints in Tanium. Please "
                "make sure that the Tanium Threat Response agent is connected properly and the "
                "hostname/IP address is correct. The JSON result has more details about the tasks."
            )
        elif not failed_entities and not_found_entities:
            output_message = (
                f"Action wasn't able to create tasks on the provided endpoints in {INTEGRATION_NAME}."
                f"Please make sure that the Tanium Threat Response agent is connected properly "
                f"and the hostname/IP address is correct."
            )
        result_value = False

    if successful_entities or failed_entities:
        entities_data = []
        for identifier, task_details in result_data["completed"].items():
            for detail in task_details:
                entities_data.append({"identifier": identifier, "task_details": detail})
        for identifier, task_details in result_data["failed"].items():
            for detail in task_details:
                entities_data.append({"identifier": identifier, "task_details": detail})
        json_results = {
            "absolute_file_path": result_data["absolute_paths"],
            "entity": entities_data,
        }
        siemplify.result.add_result_json(json_results)

    if timeout_approaching and pending_entities:
        raise Exception(
            f"action ran into a timeout during execution. Pending entities: {', '.join(pending_entities)}. "
            f"Please increase the timeout in IDE.\n"
        )

    return output_message, result_value, status


@output_handler
def main(is_first_run):
    siemplify = SiemplifyAction()
    action_start_time = unix_now()
    siemplify.script_name = DOWNLOAD_FILE_SCRIPT_NAME
    mode = "Main" if is_first_run else "Download File"
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
    file_paths = extract_action_param(
        siemplify, param_name="File Paths", is_mandatory=True, print_value=True
    )
    download_folder_path = extract_action_param(
        siemplify,
        param_name="Download Folder Path",
        is_mandatory=True,
        print_value=True,
    )
    overwrite = extract_action_param(
        siemplify,
        param_name="Overwrite",
        is_mandatory=False,
        default_value=False,
        input_type=bool,
    )

    siemplify.LOGGER.info(f"----------------- {mode} - Started -----------------")

    download_folder_path = (
        download_folder_path
        if download_folder_path.endswith("/")
        else f"{download_folder_path}/"
    )
    file_paths = convert_comma_separated_to_list(file_paths)
    result_value = False
    suitable_entities = [
        entity
        for entity in siemplify.target_entities
        if entity.entity_type in SUPPORTED_ENTITIES
    ]

    try:
        if not os.path.exists(download_folder_path):
            raise Exception(f"Folder {download_folder_path} not found.")

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
                file_paths=file_paths,
                download_folder_path=download_folder_path,
                overwrite=overwrite,
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
                download_folder_path=download_folder_path,
                overwrite=overwrite,
            )

    except Exception as err:
        output_message = (
            f"Error executing action {DOWNLOAD_FILE_SCRIPT_NAME}. Reason: {err}"
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
