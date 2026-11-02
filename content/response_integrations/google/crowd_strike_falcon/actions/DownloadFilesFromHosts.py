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
import copy
import json
import os
import sys

from soar_sdk.ScriptResult import (
    EXECUTION_STATE_COMPLETED,
    EXECUTION_STATE_FAILED,
    EXECUTION_STATE_INPROGRESS,
)
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyUtils import output_handler
from TIPCommon.extraction import extract_action_param, extract_configuration_param
from TIPCommon.transformation import string_to_multi_value

from crowd_strike_falcon.core.CrowdStrikeManager import CrowdStrikeManager
from crowd_strike_falcon.core.CrowdStrikeParser import CrowdStrikeParser
from crowd_strike_falcon.core.constants import (
    API_ROOT_DEFAULT,
    CID_ERROR,
    DOWNLOAD_FILE_FROM_HOSTS_SCRIPT_NAME,
    ENRICHMENT_PREFIX,
    ENTITIES_MAPPER,
    INTEGRATION_NAME,
    PRODUCT_NAME,
)
from crowd_strike_falcon.core.exceptions import (
    FolderNotFoundException,
    NoSuitableEntitiesException,
    NotExistingFilenamesException,
)
from crowd_strike_falcon.core.utils import (
    MockEntity,
    get_entity_original_identifier,
    save_attachment,
    validate_device_id,
)


FILENAME = "{}_{}.7z"


def start_operation(siemplify, manager, suitable_entities, filenames, cid=None):
    """Initiates an operation to start device sessions and process batch commands for
        given entities and filenames.

    Args:
        siemplify (SiemplifyManager): The Siemplify manager instance for logging and
            other operations.
        manager (DeviceManager): The device manager instance responsible for device
            operations.
        suitable_entities (list): A list of entities to process.
        filenames (list): A list of filenames to process in the batch commands.
        cid (str, optional): The customer ID for device search.Defaults to None.

    Returns:
        tuple: A tuple containing:
            - output_message (str): A message detailing the success and
                failure of the operation.
            - result_value (dict | bool): A dictionary with the results of the
                in-progress, completed, and failed operations, or False if
                no successful operations were performed.
            - status (str): The execution state of the operation, either
                'in progress' or 'completed'.
    """
    failed_entities, successful_entities, result_value = [], [], {}
    output_message = ""
    result_value = {
        "in_progress": {},
        "completed": {},
        "failed_filenames": {},
        "failed": [],
        "failed_by_session": [],
    }
    status = EXECUTION_STATE_INPROGRESS
    seen_devices = {}

    for entity in suitable_entities:
        entity_identifier = get_entity_original_identifier(entity)
        if entity.entity_type == "DEVICE_ID":
            try:
                device_info = manager.get_devices(devices_ids=[entity_identifier])
                devices = [entity_identifier] if device_info else []
            except Exception:
                devices = []
        else:
            request_filter = {
                key: entity_identifier for key in ENTITIES_MAPPER[entity.entity_type]
                }
            request_filter["cid"] = cid
            devices = manager.search_device_ids(**request_filter)

        if not devices:
            failed_entities.append(entity_identifier)
            result_value["failed"].append(entity_identifier)
            continue

        device_id = devices[0]
        if device_id in seen_devices:
            siemplify.LOGGER.info(
                f"Identifier '{entity_identifier}' maps to device ID '{device_id}', which is already "
                f"associated with entity '{seen_devices[device_id]}'. Skipping duplication."
            )
            continue
        seen_devices[device_id] = entity_identifier
        try:
            batch_session = manager.start_device_session(device_id=device_id)
            if not batch_session.completed:
                raise
        except Exception as e:
            failed_entities.append(entity_identifier)
            result_value["failed_by_session"].append(entity_identifier)
            siemplify.LOGGER.error(
                f"An error occurred on entity {entity_identifier}: Unable to create session."
            )
            siemplify.LOGGER.exception(e)
            continue

        result_value["in_progress"][entity_identifier] = []
        result_value["failed_filenames"][entity_identifier] = []
        for filename in filenames:
            try:
                batch_request_id = manager.batch_get_command(
                    batch_id=batch_session.batch_id, filename=filename
                )
                result_value["in_progress"][entity_identifier].append(batch_request_id)
            except Exception as e:
                result_value["failed_filenames"][entity_identifier].append(filename)
                siemplify.LOGGER.error(
                    f"An error occurred on entity {entity_identifier}"
                )
                siemplify.LOGGER.exception(e)

        if result_value["in_progress"][entity_identifier]:
            successful_entities.append(entity_identifier)

    if successful_entities:
        output_message = (
            f"Successfully created sessions for the following endpoints in {PRODUCT_NAME}: "
            f'{", ".join(successful_entities)}\n'
        )
        result_value = json.dumps(result_value)
        if failed_entities:
            output_message += (
                f"Action wasn't able to created sessions for the following endpoints in "
                f'{PRODUCT_NAME}: {", ".join(failed_entities)}\n'
            )
    else:
        if not result_value["failed_by_session"]:
            output_message = (
                f"None of the provided endpoints were found in {PRODUCT_NAME}.\n"
            )
        elif not result_value["failed"]:
            output_message = f"Action wasn't able to create sessions for provided endpoints in {PRODUCT_NAME}.\n"
        else:
            if result_value["failed_by_session"]:
                output_message += (
                    f"Action wasn't able to create sessions for the following endpoints in "
                    f'{PRODUCT_NAME}: {", ".join(result_value["failed_by_session"])}\n'
                )
            if result_value["failed"]:
                output_message += (
                    f"The following endpoints were not found in "
                    f'{PRODUCT_NAME}: {", ".join(result_value["failed"])}\n'
                )
        if result_value["failed_filenames"]:
            output_message += (
                f"File {', '.join(filenames)} wasn't found on the provided "
                f"endpoints in {PRODUCT_NAME}."
            )
        result_value = False
        status = EXECUTION_STATE_COMPLETED

    return output_message, result_value, status


def query_operation_status(
    siemplify, manager, processes_data, suitable_entities, folder_path
):
    mutable_data = copy.deepcopy(processes_data)
    for entity, batch_request_ids in processes_data["in_progress"].items():
        if not mutable_data["completed"].get(entity, []):
            mutable_data["completed"][entity] = []
        for batch_request_id in batch_request_ids:
            try:
                batch_command = manager.get_status_of_batch_command(
                    batch_request_id=batch_request_id
                )

                if batch_command:
                    siemplify.LOGGER.info(batch_command)
                    mutable_data["completed"][entity].append(batch_command[0].to_json())
                    mutable_data["in_progress"][entity].remove(batch_request_id)
            except Exception as e:
                siemplify.LOGGER.error(
                    f"An error occurred on batch id {batch_request_id}"
                )
                siemplify.LOGGER.exception(e)

    not_finished_entities = [
        entity for entity, data_list in mutable_data["in_progress"].items() if data_list
    ]
    if not_finished_entities:
        status = EXECUTION_STATE_INPROGRESS
        result_value = json.dumps(mutable_data)
        in_progress_entities = [
            entity for entity, items in mutable_data["in_progress"].items() if items
        ]
        output_message = (
            f"Waiting for results for the following entities: "
            f"{', '.join(in_progress_entities)}"
        )
    else:
        output_message, result_value, status = finish_operation(
            siemplify=siemplify,
            manager=manager,
            suitable_entities=suitable_entities,
            result_data=mutable_data,
            folder_path=folder_path,
        )

    return output_message, result_value, status


def finish_operation(siemplify, manager, suitable_entities, result_data, folder_path):
    result_value = True
    status = EXECUTION_STATE_COMPLETED
    failed_entities = result_data["failed"]
    failed_entities_for_session = result_data["failed_by_session"]
    successful_entities, json_results = [], []
    output_message = ""
    failed_to_download = {}
    downloaded_files = {}
    entities_to_update = []
    for failed_file_identifier, failed_file_names in result_data.get(
        "failed_filenames", {}
    ).items():
        for failed_file_name in failed_file_names:
            failed_to_download[failed_file_name] = failed_to_download.get(
                failed_file_name, []
            )
            failed_to_download[failed_file_name].append(failed_file_identifier)

    for entity in suitable_entities:
        entity_identifier = get_entity_original_identifier(entity)
        if entity_identifier in result_data["completed"]:
            for file_data in result_data["completed"][entity_identifier]:
                file = CrowdStrikeParser().build_batch_command_obj(file_data)
                content = manager.get_file_content(file.session_id, file.sha256)
                original_file_name = os.path.basename(file.name).split("\\")[-1]
                filename = FILENAME.format(entity_identifier, original_file_name)
                save_attachment(path=folder_path, name=filename, content=content)
                downloaded_files[original_file_name] = downloaded_files.get(
                    original_file_name, []
                )
                downloaded_files[original_file_name].append(entity_identifier)
                json_results.append(os.path.join(folder_path, filename))
                successful_entities.append(entity)

    for file_identifier, file_entity in {
        get_entity_original_identifier(entity): entity
        for entity in siemplify.target_entities
        if entity.entity_type == EntityTypes.FILENAME
    }.items():
        hosts = downloaded_files.get(file_identifier)
        files_with_host = []
        if hosts:
            for host in hosts:
                files_with_host.append(
                    os.path.join(folder_path, FILENAME.format(host, file_identifier))
                )

            file_entity.is_enriched = True
            file_entity.additional_properties.update(
                {f"{ENRICHMENT_PREFIX}_filepath": ", ".join(files_with_host)}
            )
            entities_to_update.append(file_entity)
    for filename, entity_identifiers in downloaded_files.items():
        if entity_identifiers:
            output_message += (
                f"Successfully downloaded file {filename} from the following endpoints in "
                f"{PRODUCT_NAME}: {', '.join(entity_identifiers)}\n"
            )
    for filename, entity_identifiers in failed_to_download.items():
        if entity_identifiers:
            output_message += (
                f"Action wasn’t able to download file {filename} from the following endpoints in "
                f"{PRODUCT_NAME}: {', '.join(entity_identifiers)}\n"
            )

    if failed_entities_for_session:
        output_message += (
            f"Action wasn't able to create sessions for the following endpoints in "
            f'{PRODUCT_NAME}: {", ".join(failed_entities_for_session)}\n'
        )
    if failed_entities:
        output_message += (
            f"The following endpoints were not found in "
            f'{PRODUCT_NAME}: {", ".join(failed_entities)}\n'
        )
    if json_results:
        siemplify.result.add_result_json({"absolute_paths": json_results})
    if entities_to_update:
        siemplify.update_entities(entities_to_update)

    return output_message, result_value, status


@output_handler
def main(is_first_run):
    siemplify = SiemplifyAction()
    siemplify.script_name = DOWNLOAD_FILE_FROM_HOSTS_SCRIPT_NAME
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
    folder_path = extract_action_param(
        siemplify,
        param_name="Download Folder Path",
        is_mandatory=True,
        print_value=True,
    )
    overwrite = extract_action_param(
        siemplify,
        param_name="Overwrite",
        print_value=True,
        input_type=bool,
        is_mandatory=True,
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
    device_id_param = extract_action_param(
        siemplify,
        param_name="Device ID",
        print_value=True,
    )
    device_ids = string_to_multi_value(device_id_param)
    for device_id in device_ids:
        suitable_entities.append(MockEntity(device_id, "DEVICE_ID"))
    filenames = [
        get_entity_original_identifier(entity)
        for entity in siemplify.target_entities
        if entity.entity_type == EntityTypes.FILENAME
    ]

    try:
        validate_device_id(device_id_param)
        manager = CrowdStrikeManager(
            client_id=client_id,
            client_secret=client_secret,
            use_ssl=use_ssl,
            api_root=api_root,
            force_check_connectivity=True,
            customer_id=customer_id,
        )

        if not filenames:
            raise NotExistingFilenamesException

        if not suitable_entities:
            raise NoSuitableEntitiesException

        if folder_path[0] != "/":
            raise FolderNotFoundException

        existing_files_from_filenames, full_paths = get_existing_files_from_directory(
            filenames, suitable_entities, folder_path
        )
        if not overwrite and existing_files_from_filenames:
            raise Exception(
                f'files with path {", ".join(full_paths)} already exists. '
                f'Please delete the files or set "Overwrite" to true.'
            )

        if is_first_run:
            output_message, result_value, status = start_operation(
                siemplify,
                manager=manager,
                suitable_entities=suitable_entities,
                filenames=filenames,
                cid=customer_id,
            )
        if status == EXECUTION_STATE_INPROGRESS:
            processes_data = (
                result_value
                if result_value
                else extract_action_param(
                    siemplify, param_name="additional_data", default_value="{}"
                )
            )

            output_message, result_value, status = query_operation_status(
                siemplify=siemplify,
                manager=manager,
                processes_data=json.loads(processes_data),
                suitable_entities=suitable_entities,
                folder_path=folder_path,
            )

    except Exception as e:
        error_message = (
            f"Error executing action {DOWNLOAD_FILE_FROM_HOSTS_SCRIPT_NAME}. "
            f"Reason: "
        )
        output_message = f"{error_message} {e}"

        if CID_ERROR in str(e).lower():
            output_message = f"{error_message} Incorrect Customer ID specified."

        if isinstance(e, NotExistingFilenamesException) or isinstance(
            e, NoSuitableEntitiesException
        ):
            output_message += "Not enough entities in the scope of the action."
        if isinstance(e, FolderNotFoundException):
            output_message += "Folder not found."

        status = EXECUTION_STATE_FAILED
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
        result_value = False

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    log_message = (
        f"\n  status: {status}\n"
        f"  is_success: {result_value}\n"
        f"  output_message: {output_message}"
    )
    siemplify.LOGGER.info(log_message)
    siemplify.end(output_message, result_value, status)


def get_existing_files_from_directory(filenames, entities, path):
    existing_files = []
    full_paths = []
    for entity in entities:
        for filename in filenames:
            local_path = os.path.join(path, FILENAME.format(entity, filename))
            if os.path.exists(local_path):
                existing_files.append(FILENAME.format(entity, filename))
                full_paths.append(local_path)

    return existing_files, full_paths


if __name__ == "__main__":
    is_first_run = len(sys.argv) < 3 or sys.argv[2] == "True"
    main(is_first_run)
