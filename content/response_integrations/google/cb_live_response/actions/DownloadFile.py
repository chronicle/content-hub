from __future__ import annotations
import copy
import os
import json
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.ScriptResult import EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyDataModel import EntityTypes
from TIPCommon import extract_configuration_param, extract_action_param
from ..core.constants import DOWNLOAD_FILE_SCRIPT_NAME, INTEGRATION_NAME
from ..core.Factory import ManagerFactory
from ..core.AsyncActionStepHandler import (
    ActionStep,
    FAILED_ENTITY_STATE,
    ENTITY_FILENAME_CONCAT_CHAR,
    IN_PROGRESS_ENTITY_STATE,
    ALL_FAILED_MSG,
    SOME_COMPLETED_MSG,
    SOME_FAILED_MSG,
)
from ..core.utils import (
    get_entity_original_identifier,
    save_attachment,
    validate_local_path,
    string_to_multi_value,
)
from ..core.CBLiveResponseActionSteps import (
    format_output_message,
    device_custom_output_messages,
)
from ..core.AsyncActionStepHandlerMultiple import AsyncActionStepHandlerMultiple

SUPPORTED_ENTITY_TYPES = [EntityTypes.ADDRESS, EntityTypes.HOSTNAME]
INITIAL_STEP = "initial_step"
DEVICE_GETTER = "device"
SESSION_STARTER = "session_starter"
SESSION_CHECKER = "session_status"
DIRECTORY_COMMAND = "directory_data_command"
DIRECTORY_COMMAND_CHECKER = "directory_command_object"
COMMAND_STARTER = "command"
COMMAND_CHECKER = "command_object"
MULTIPLE_DEVICES = "multiple_devices"
DUPLICATED_DEVICES = "duplicated_devices"

ACTION_COMPLETE_OUTPUT_MESSAGES = {ALL_FAILED_MSG: "No files were downloaded."}

FAILED_OUTPUT_MESSAGE = (
    "Action failed to download a file {filename} for the following entities: {entities}"
)
SUCCESSFUL_OUTPUT_MESSAGE = (
    "Downloaded file {filename} to local path {local_path} for the following entities: "
    "{entities}"
)

FILENAME_PATH_CONCAT = FILEPATH_PATH_CONCAT = "_|_"
FILENAME_PATH_VARIABLE = "L_P"
FILEPATH_PATH_VARIABLE = "P_P"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = DOWNLOAD_FILE_SCRIPT_NAME

    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Root",
        is_mandatory=True,
    )
    org_key = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Organization Key",
        is_mandatory=True,
    )
    cb_cloud_api_id = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Carbon Black Cloud API ID",
        is_mandatory=True,
    )
    cb_cloud_api_secret_key = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Carbon Black Cloud API Secret Key",
        is_mandatory=True,
    )
    lr_api_id = extract_configuration_param(
        siemplify, provider_name=INTEGRATION_NAME, param_name="Live Response API ID"
    )
    lr_api_secret_key = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Live Response API Secret Key",
    )
    use_new_api_version = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        input_type=bool,
        param_name="Use Live Response V6 API",
    )

    filename = string_to_multi_value(
        extract_action_param(siemplify, param_name="File Name", print_value=True)
    )
    remote_dir_path = string_to_multi_value(
        extract_action_param(
            siemplify, param_name="Remote Directory Path", print_value=True
        )
    )
    local_path = string_to_multi_value(
        extract_action_param(
            siemplify,
            param_name="Local Directory Path",
            print_value=True,
            is_mandatory=True,
        )
    )
    executing_limit_per_entity = extract_action_param(
        siemplify,
        param_name="Check for active session x times",
        print_value=True,
        input_type=int,
        is_mandatory=True,
    )

    filenames = original_filenames = (
        filename
        if filename
        else [
            get_entity_original_identifier(entity)
            for entity in siemplify.target_entities
            if entity.entity_type == EntityTypes.FILENAME
        ]
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    json_result = {}
    working_only_with_paths = False
    suitable_entities = [
        entity
        for entity in siemplify.target_entities
        if entity.entity_type in SUPPORTED_ENTITY_TYPES
    ]
    sorted_suitable_entities = sorted(
        suitable_entities,
        key=lambda entity: entity.entity_type == EntityTypes.HOSTNAME,
        reverse=True,
    )

    try:
        if not remote_dir_path:
            if not filenames:
                raise Exception(
                    "Action failed to start since both Filename Remote Directory Path were not provided."
                )
            if not is_all_filenames_with_folders(filenames):
                raise Exception(
                    "Action failed to start since some of the elements specified as a placeholder for the "
                    "File Name are full path, and some are not."
                )
            if len(filenames) != len(local_path):
                raise Exception(
                    "Action failed to start since the number of elements specified in File Name and Remote "
                    "Directory and/or Local Directory Path action input parameters are different"
                )

        if remote_dir_path and filenames and local_path:
            if not is_all_filenames_without_folders(filenames):
                raise Exception(
                    "Action failed to start since some of the elements specified as a placeholder for "
                    "the File Name are full path, and some are not."
                )
            if not (len(filenames) == len(remote_dir_path) == len(local_path)):
                raise Exception(
                    "Action failed to start since the number of elements specified in File Name and Remote "
                    "Directory and/or Local Directory Path action input parameters are different"
                )

        if not filenames:
            if len(remote_dir_path) > 1:
                raise Exception(
                    "Action failed to start since the option to download all files from the directory is "
                    "supported only for one directory at a time."
                )

            if len(remote_dir_path) != len(local_path):
                raise Exception(
                    "Action failed to start since the number of elements specified in File Name and Remote "
                    "Directory and/or Local Directory Path action input parameters are different"
                )

            working_only_with_paths = True
            filenames = ["dummy_filename.txt"] * len(remote_dir_path)

        for path in local_path:
            validate_local_path(path)

        manager = ManagerFactory.create_manager(
            api_root=api_root,
            org_key=org_key,
            cb_cloud_api_id=cb_cloud_api_id,
            cb_cloud_api_secret_key=cb_cloud_api_secret_key,
            lr_api_id=lr_api_id,
            lr_api_secret_key=lr_api_secret_key,
            force_check_connectivity=True,
            use_new_api_version=use_new_api_version,
        )

        action_steps = {
            0: ActionStep(
                step_id=INITIAL_STEP,
                step_label="Initial step",
                method_name="initial_step",
                variables={
                    "suitable_entities": [
                        get_entity_original_identifier(entity)
                        for entity in sorted_suitable_entities
                    ],
                    "filenames": filenames,
                    "directory_paths": remote_dir_path,
                    "working_only_with_paths": working_only_with_paths,
                    "local_paths": local_path,
                },
            ),
            1: ActionStep(
                step_id=DEVICE_GETTER,
                step_label="Get Corresponding CB Cloud Device",
                method_name="get_device_id_by_item",
            ),
            2: ActionStep(
                step_id=SESSION_STARTER,
                step_label="Session Start",
                method_name="session_start",
                variables={"previous_step": DEVICE_GETTER},
            ),
            3: ActionStep(
                step_id=SESSION_CHECKER,
                step_label="Session Check",
                method_name="session_status_check_by_item",
                retry=executing_limit_per_entity,
                wait_before_retry=2,
                variables={"previous_step": SESSION_STARTER},
            ),
            4: (
                ActionStep(
                    step_id=DIRECTORY_COMMAND,
                    step_label="Create Command Get Directory Data",
                    method_name="get_directory_data",
                    variables={"directory_paths": remote_dir_path},
                )
                if remote_dir_path and not original_filenames
                else None
            ),
            5: (
                ActionStep(
                    step_id=DIRECTORY_COMMAND_CHECKER,
                    step_label="Command Check Get Directory Data",
                    method_name="command_check_get_directory_data",
                    retry=5,
                    wait_before_retry=30,
                )
                if remote_dir_path and not original_filenames
                else None
            ),
            6: ActionStep(
                step_id=COMMAND_STARTER,
                step_label="Command Start",
                method_name="command_start",
            ),
            7: ActionStep(
                step_id=COMMAND_CHECKER,
                step_label="Command Check",
                method_name="command_check",
                retry=5,
                wait_before_retry=30,
                variables={"json_result": json_result},
            ),
        }
        action_steps = {
            key: value
            for key, value in action_steps.items()
            if isinstance(value, ActionStep)
        }
        action_steps = {
            index: value for index, value in enumerate(action_steps.values())
        }

        result_value = json.loads(
            extract_action_param(
                siemplify, param_name="additional_data", default_value="{}"
            )
        )
        step_handler = AsyncActionStepHandlerMultiple(
            siemplify, manager, action_steps, result_value, globals()
        )
        output_message, result_value, status = step_handler.execute_steps()
        if isinstance(result_value, dict):
            result_value = json.dumps(result_value)

    except Exception as e:
        output_message = (
            f"Failed to execute {DOWNLOAD_FILE_SCRIPT_NAME} action! Error is {e}"
        )
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        result_value = False

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  is_success: {result_value}\n  output_message: {output_message}"
    )
    siemplify.end(output_message, result_value, status)


def initial_step(
    step_handler,
    suitable_entities,
    filenames,
    directory_paths,
    working_only_with_paths,
    local_paths,
):
    if directory_paths:
        file_names = []
        for index, path in enumerate(directory_paths):
            file_names.append(os.path.join(path, filenames[index]))
        filenames = file_names

    for entity_identifier in suitable_entities:
        for filename in filenames:
            step_handler.logger.info(f"Initiating entity {entity_identifier}")
            step_handler.add_entity_data_to_step(
                f"{entity_identifier}{ENTITY_FILENAME_CONCAT_CHAR}{filename}",
                entity_identifier,
            )
            step_handler.logger.info(f"Entity {entity_identifier} is ready.")

    if not working_only_with_paths:
        filename_path_combination = []
        for index, path in enumerate(local_paths):
            filename_path_combination.append(
                f"{filenames[index]}{FILENAME_PATH_CONCAT}{path}"
            )
            step_handler.add_custom_variable(
                FILENAME_PATH_VARIABLE, filename_path_combination
            )
    else:
        filepath_localpath_combination = []
        for index, path in enumerate(local_paths):
            filepath_localpath_combination.append(
                f"{filenames[index]}{FILENAME_PATH_CONCAT}{path}"
            )
            step_handler.add_custom_variable(
                FILENAME_PATH_VARIABLE, filepath_localpath_combination
            )
            step_handler.add_custom_variable(FILEPATH_PATH_VARIABLE, True)


def get_directory_data(step_handler, directory_paths):
    for directory_path in directory_paths:
        for item in step_handler.get_entities_by_state(state=IN_PROGRESS_ENTITY_STATE):
            entity_identifier = step_handler.extract_entities_from_item(item)
            filename = step_handler.extract_entities_from_item(item, 1)
            session_id = step_handler.get_entity_data(item, SESSION_STARTER)
            if directory_path not in filename:
                continue

            try:
                step_handler.logger.info(f"Start processing entity {entity_identifier}")
                step_handler.logger.info(f"Starting command for list files")
                command = step_handler.manager.start_command_for_list_files(
                    session_id=session_id, directory_path=directory_path
                )
                step_handler.add_entity_data_to_step(item, command.id)
            except Exception as err:
                err_msg = f"An error occurred while getting data about command for session {session_id}. Error is {err}"
                step_handler.logger.error(err_msg)
                step_handler.logger.exception(err)
                step_handler.fail_entity(item, reason=err_msg)
            step_handler.logger.info(f"Finishing processing entity {entity_identifier}")


def command_check_get_directory_data(step_handler):
    in_progress_entities = copy.deepcopy(
        step_handler.get_entities_by_state(state=IN_PROGRESS_ENTITY_STATE)
    )
    local_paths = step_handler.get_custom_variable(FILENAME_PATH_VARIABLE)
    for item in in_progress_entities:
        entity_identifier = step_handler.extract_entities_from_item(item)
        filename = step_handler.extract_entities_from_item(item, 1)
        local_path = [item for item in local_paths if filename in item][0].split(
            FILENAME_PATH_CONCAT
        )[-1]
        session_id = step_handler.get_entity_data(item, SESSION_STARTER)
        command_id = step_handler.get_entity_data(item, DIRECTORY_COMMAND)
        step_handler.logger.info(f"Start process entity {entity_identifier}")

        try:
            step_handler.logger.info(f"Getting command")
            command = step_handler.manager.get_command_by_id(
                session_id=session_id, command_id=command_id
            )
            if command.is_completed or command.is_failed:
                if command.files:
                    step_handler.add_entity_data_to_step(
                        item, f"{command.id}{command.name}"
                    )

                    updatable_data, filename_path_combination = {}, []
                    for file in command.files:
                        item_key = (
                            f"{entity_identifier}{ENTITY_FILENAME_CONCAT_CHAR}"
                            f"{os.path.join(command.input_name, file.filename)}"
                        )
                        filename_path_combination.append(
                            f"{os.path.join(command.input_name, file.filename)}"
                            f"{FILENAME_PATH_CONCAT}{local_path}"
                        )
                        updatable_data[item_key] = copy.deepcopy(
                            step_handler.get_full_entity_data(item)
                        )
                    step_handler.update_entity_mapping_with_dict(updatable_data)
                    step_handler.remove_entity(item)
                    step_handler.add_custom_variable(
                        FILENAME_PATH_VARIABLE, filename_path_combination
                    )
                else:
                    step_handler.fail_entity(item, reason="No file found")
        except Exception as err:
            err_msg = f"An error occurred while getting data about command {command_id} for session {session_id}."
            step_handler.logger.error(err_msg)
            step_handler.logger.exception(err)
            step_handler.fail_entity(item, reason=err_msg)


def command_start(step_handler):
    for item in step_handler.get_entities_by_state(state=IN_PROGRESS_ENTITY_STATE):
        entity_identifier = step_handler.extract_entities_from_item(item)
        filename = step_handler.extract_entities_from_item(item, 1)
        session_id = step_handler.get_entity_data(item, SESSION_STARTER)

        step_handler.logger.info(f"Start processing entity {entity_identifier}")
        try:
            step_handler.logger.info(f"Starting command for get files")
            command = step_handler.manager.start_command_for_get_file(
                session_id=session_id, path=filename
            )
            step_handler.add_entity_data_to_step(item, command.id)
        except Exception as err:
            err_msg = f"An error occurred while getting data about command for session {session_id}. Error is {err}"
            step_handler.logger.error(err_msg)
            step_handler.logger.exception(err)
            step_handler.fail_entity(item, reason=err_msg)
        step_handler.logger.info(f"Finishing processing entity {entity_identifier}")


def command_check(step_handler, json_result):
    local_paths = step_handler.get_custom_variable(FILENAME_PATH_VARIABLE)
    completed_output_messages, already_downloaded_files = [], {}
    for item in step_handler.get_entities_by_state(state=IN_PROGRESS_ENTITY_STATE):
        entity_identifier = step_handler.extract_entities_from_item(item)
        filename = step_handler.extract_entities_from_item(item, 1)
        local_path = [item for item in local_paths if filename in item][0].split(
            FILENAME_PATH_CONCAT
        )[-1]
        step_handler.logger.info(f"Start process entity {entity_identifier}")
        session_id = step_handler.get_entity_data(item, SESSION_STARTER)
        command_id = step_handler.get_entity_data(item, COMMAND_STARTER)

        try:
            step_handler.logger.info(f"Getting command")
            command = step_handler.manager.get_command_by_id(
                session_id=session_id, command_id=command_id
            )
            if command.is_completed or command.is_failed:
                step_handler.logger.info(f"Command is ready.")
                if command.details and command.is_completed:
                    file_content = step_handler.manager.get_file_content(
                        session_id=session_id, file_id=command.details.file_id
                    )
                    filename_to_save = get_file_parts(filename)
                    if filename_to_save in already_downloaded_files.values():
                        filename_to_save = f"{entity_identifier}_{filename_to_save}"
                        step_handler.logger.info(
                            f"File {filename_to_save} already downloaded. Adding "
                            f"host as a prefix"
                        )
                    save_attachment(
                        path=local_path, name=filename_to_save, content=file_content
                    )
                    already_downloaded_files[entity_identifier] = filename_to_save
                    step_handler.add_entity_data_to_step(item, command)
                    json_result = collect_json_result(
                        step_handler,
                        item,
                        command,
                        json_result,
                        os.path.join(local_path, filename_to_save),
                    )
                    completed_output_messages.append(
                        SUCCESSFUL_OUTPUT_MESSAGE.format(
                            filename=filename,
                            local_path=local_path,
                            entities=entity_identifier,
                        )
                    )
                else:
                    err_msg = f"Command with id {command_id} ready with no result."
                    step_handler.fail_entity(item, reason=err_msg)
                    step_handler.failed_entity_json[item] = command.to_json()
        except Exception as err:
            err_msg = (
                f"An error occurred while getting data about command {command_id} for session {session_id}. "
                f"Error is {err} "
            )
            step_handler.logger.error(err_msg)
            step_handler.logger.exception(err)
            step_handler.fail_entity(item, reason=err_msg)
        step_handler.logger.info(f"Finishing processing entity {entity_identifier}")
    if json_result:
        step_handler.json_result = json_result
    step_handler.add_output_messages(
        get_output_message(step_handler, completed_output_messages)
    )
    add_custom_output_messages(step_handler)


def add_custom_output_messages(step_handler):
    message = device_custom_output_messages(step_handler)

    if message:
        step_handler.add_addition_output_message(message)


def format_success_output_message(success_messages):
    return "\n".join(success_messages)


def get_output_message(step_handler, success_messages):
    ACTION_COMPLETE_OUTPUT_MESSAGES.update(
        {
            SOME_COMPLETED_MSG: format_success_output_message(success_messages),
            SOME_FAILED_MSG: format_output_message(
                step_handler, FAILED_OUTPUT_MESSAGE, FAILED_ENTITY_STATE
            ),
        }
    )
    return ACTION_COMPLETE_OUTPUT_MESSAGES


def collect_json_result(step_handler, item, command, json_result, filename):
    json_result[step_handler.extract_entities_from_item(item)] = json_result.get(
        step_handler.extract_entities_from_item(item), []
    )
    result = command.to_json()
    result.update({"absolute_file_path": filename})
    json_result[step_handler.extract_entities_from_item(item)].append(result)
    return json_result


def is_all_filenames_with_folders(filenames):
    for filename in filenames:
        if not any(x in filename for x in ["/", "\\"]):
            return False

    return True


def is_all_filenames_without_folders(filenames):
    for filename in filenames:
        if any(x in filename for x in ["/", "\\"]):
            return False

    return True


def get_file_parts(filename, position=-1):
    if "/" in filename:
        return filename.split("/")[position]
    elif "\\" in filename:
        return filename.split("\\")[position]

    return filename


if __name__ == "__main__":
    main()
