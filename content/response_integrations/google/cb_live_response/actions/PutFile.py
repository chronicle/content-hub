from __future__ import annotations
import json
import os
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.ScriptResult import EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from TIPCommon import extract_configuration_param, extract_action_param
from ..core.constants import PUT_FILE_SCRIPT_NAME, INTEGRATION_NAME
from ..core.utils import get_entity_original_identifier, string_to_multi_value
from ..core.Factory import ManagerFactory
from ..core.AsyncActionStepHandler import (
    ActionStep,
    FAILED_ENTITY_STATE,
    IN_PROGRESS_ENTITY_STATE,
    IN_PROGRESS_MSG,
    ALL_FAILED_MSG,
    SOME_COMPLETED_MSG,
    SOME_FAILED_MSG,
    ENTITY_KEY_FOR_FORMAT,
    ENTITY_FILENAME_CONCAT_CHAR,
)
from ..core.CBLiveResponseActionSteps import (
    device_custom_output_messages,
    format_output_message,
)
from ..core.AsyncActionStepHandlerMultiple import AsyncActionStepHandlerMultiple

SUPPORTED_ENTITY_TYPES = [EntityTypes.ADDRESS, EntityTypes.HOSTNAME]
FILENAME_PATH_CONCAT = "_|_"
FILENAME_PATH_VARIABLE = "S_P"
CUSTOM_MESSAGE = "C_M"

INITIAL_STEP = "initial_step"
DEVICE_GETTER = "device"
SESSION_STARTER = "session_starter"
SESSION_CHECKER = "session_status"
FILE_UPLOADER = "file_upload"
COMMAND_STARTER = "command"
COMMAND_CHECKER = "command_object"
MULTIPLE_DEVICES = "multiple_devices"
DUPLICATED_DEVICES = "duplicated_devices"

ACTION_COMPLETE_OUTPUT_MESSAGES = {
    IN_PROGRESS_MSG: f"Action reached timeout waiting for results for the following entities: {{{ENTITY_KEY_FOR_FORMAT}}}",
    ALL_FAILED_MSG: "No files were uploaded.",
}
FAILED_OUTPUT_MESSAGE = (
    "Action failed to upload a file {filename} for the following entities: {entities}"
)
SUCCESSFUL_OUTPUT_MESSAGE = "Uploaded file {filename} to remote path {local_path} for the following entities: {entities}"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = PUT_FILE_SCRIPT_NAME
    siemplify.LOGGER.info(f"----------------- Main - Param Init -----------------")

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
    source_file_path = string_to_multi_value(
        extract_action_param(
            siemplify, param_name="Source Directory Path", print_value=True
        )
    )
    destination_directory_path = string_to_multi_value(
        extract_action_param(
            siemplify,
            print_value=True,
            is_mandatory=True,
            param_name="Destination Directory Path",
        )
    )
    executing_limit_per_entity = extract_action_param(
        siemplify,
        param_name="Check for active session x times",
        print_value=True,
        is_mandatory=True,
        input_type=int,
    )

    filenames = (
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
        for path in source_file_path:
            if not os.path.exists(path):
                raise Exception(f"No such directory in: {path}.")

        if not source_file_path:
            if not filenames:
                raise Exception(
                    "Action failed to start since both Filename Source Directory Path were not provided."
                )
            if not is_all_filenames_with_folders(filenames):
                raise Exception(
                    "Action failed to start since some of the elements specified as a placeholder for the"
                    " File Name are full path, and some are not."
                )

        if source_file_path and filenames and destination_directory_path:
            if not is_all_filenames_without_folders(filenames):
                raise Exception(
                    "Action failed to start since some of the elements specified as a placeholder for "
                    "the File Name are full path, and some are not."
                )
            if not (
                len(filenames)
                == len(source_file_path)
                == len(destination_directory_path)
            ):
                raise Exception(
                    "Action failed to start since the number of elements specified in File Name and Source "
                    "Directory Path and/or Destination Directory Path action input parameters are different"
                )

        if not filenames:
            raise Exception(
                "Action failed to start since Filename was not provided either as Siemplify Entity or "
                "action input parameter."
            )

        siemplify.LOGGER.info("Connecting to Carbon Black Defense.")
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
                    "source_paths": source_file_path,
                    "destination_paths": destination_directory_path,
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
            4: ActionStep(
                step_id=FILE_UPLOADER,
                step_label="Upload File",
                method_name="upload_file",
            ),
            5: ActionStep(
                step_id=COMMAND_STARTER,
                step_label="Command Start",
                method_name="command_start",
            ),
            6: ActionStep(
                step_id=COMMAND_CHECKER,
                step_label="Command Check",
                method_name="command_check",
                retry=5,
                wait_before_retry=30,
                variables={"json_result": json_result},
            ),
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
            f"Failed to execute {PUT_FILE_SCRIPT_NAME} action! Error is {e}"
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
    step_handler, suitable_entities, filenames, source_paths, destination_paths
):
    if source_paths:
        file_names = []
        for index, path in enumerate(source_paths):
            file_names.append(os.path.join(path, filenames[index]))
        filenames = file_names

    if destination_paths:
        filename_path_combination = []
        for index, path in enumerate(destination_paths):
            filename_path_combination.append(
                f"{filenames[index]}{FILENAME_PATH_CONCAT}{path}"
            )
        step_handler.add_custom_variable(
            FILENAME_PATH_VARIABLE, filename_path_combination
        )

    for entity_identifier in suitable_entities:
        for filename in filenames:
            step_handler.logger.info(f"Initiating entity {entity_identifier}")
            step_handler.add_entity_data_to_step(
                f"{entity_identifier}{ENTITY_FILENAME_CONCAT_CHAR}{filename}",
                entity_identifier,
            )
            step_handler.logger.info(f"Entity {entity_identifier} is ready.")
    step_handler.add_custom_variable(CUSTOM_MESSAGE, [])


def upload_file(step_handler):
    failed_entities = []
    for item in step_handler.get_entities_by_state(state=IN_PROGRESS_ENTITY_STATE):
        entity_identifier = step_handler.extract_entities_from_item(item)
        filename = step_handler.extract_entities_from_item(item, 1)
        step_handler.logger.info(f"Start process entity {entity_identifier} ")
        session_id = step_handler.get_entity_data(item, SESSION_STARTER)
        try:
            file = step_handler.manager.upload_file(session_id, file_path=filename)
            step_handler.add_entity_data_to_step(item, file.id)
        except Exception as e:
            err_msg = f"Failed to upload file in LR session entity {entity_identifier}. Error is {e}."
            step_handler.logger.error(err_msg)
            step_handler.logger.exception(e)
            step_handler.fail_entity(item, reason=err_msg)
            failed_entities.append((filename, entity_identifier))
        step_handler.logger.info(f"Finishing processing entity {entity_identifier}")
    message = ""
    for filename, entity in failed_entities:
        message += f"Action failed to upload a file {filename} for the following entities: {entity} \n"
    step_handler.add_output_messages({SOME_FAILED_MSG: message})


def command_start(step_handler):
    destination_directory_paths = step_handler.get_custom_variable(
        FILENAME_PATH_VARIABLE
    )
    for item in step_handler.get_entities_by_state(state=IN_PROGRESS_ENTITY_STATE):
        entity_identifier = step_handler.extract_entities_from_item(item)
        step_handler.logger.info(f"Start processing entity {entity_identifier}")
        session_id = step_handler.get_entity_data(item, SESSION_STARTER)
        filename = step_handler.extract_entities_from_item(item, 1)
        destination_directory_path = [
            item for item in destination_directory_paths if filename in item
        ][0].split(FILENAME_PATH_CONCAT)[-1]
        file_name = get_file_parts(filename)
        file_id = step_handler.get_entity_data(item, FILE_UPLOADER)
        try:
            command = step_handler.manager.initiate_put_file_command(
                session_id=session_id,
                file_id=file_id,
                destination_file_path=os.path.join(
                    destination_directory_path, file_name
                ),
            )
            step_handler.add_entity_data_to_step(item, command.id)
        except Exception as err:
            err_msg = f"An error occurred while getting data about command for session {session_id}. Error is {err}."
            step_handler.logger.error(err_msg)
            step_handler.logger.exception(err)
            step_handler.fail_entity(item, reason=err_msg)
        step_handler.logger.info(f"Finishing processing entity {entity_identifier}")


def command_check(step_handler, json_result):
    step_handler.add_output_messages(ACTION_COMPLETE_OUTPUT_MESSAGES)
    destination_directory_paths = step_handler.get_custom_variable(
        FILENAME_PATH_VARIABLE
    )
    for item in step_handler.get_entities_by_state(state=IN_PROGRESS_ENTITY_STATE):
        entity_identifier = step_handler.extract_entities_from_item(item)
        filename = step_handler.extract_entities_from_item(item, 1)
        local_path = [item for item in destination_directory_paths if filename in item][
            0
        ].split(FILENAME_PATH_CONCAT)[-1]

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
                if command.is_completed:
                    json_result = collect_json_result(
                        step_handler, item, command, filename, local_path, json_result
                    )
                    step_handler.add_entity_data_to_step(item, command)
                    custom_success_message = step_handler.get_custom_variable(
                        CUSTOM_MESSAGE
                    )
                    custom_success_message.append(
                        SUCCESSFUL_OUTPUT_MESSAGE.format(
                            filename=filename,
                            local_path=local_path,
                            entities=entity_identifier,
                        )
                    )
                    step_handler.add_custom_variable(
                        CUSTOM_MESSAGE, custom_success_message
                    )
                else:
                    err_msg = f"Command with id {command_id} ready with no result."
                    step_handler.fail_entity(item, reason=err_msg)
                    step_handler.failed_entity_json[item] = command.to_json()
        except Exception as err:
            err_msg = (
                f"An error occurred while getting data about command {command_id} for session {session_id}."
                f" Error is {err}."
            )
            step_handler.logger.error(err_msg)
            step_handler.logger.exception(err)
            step_handler.fail_entity(item, reason=err_msg)

        step_handler.logger.info(f"Finishing processing entity {entity_identifier}")
    if json_result:
        step_handler.json_result = json_result
    step_handler.add_output_messages(get_output_message(step_handler))
    add_custom_output_messages(step_handler)


def add_custom_output_messages(step_handler):
    message = device_custom_output_messages(step_handler)

    if message:
        step_handler.add_addition_output_message(message)


def format_success_output_message(step_handler):
    return "\n".join(step_handler.get_custom_variable(CUSTOM_MESSAGE))


def get_output_message(step_handler):
    ACTION_COMPLETE_OUTPUT_MESSAGES.update(
        {
            SOME_COMPLETED_MSG: format_success_output_message(step_handler),
            SOME_FAILED_MSG: format_output_message(
                step_handler, FAILED_OUTPUT_MESSAGE, FAILED_ENTITY_STATE
            ),
        }
    )
    return ACTION_COMPLETE_OUTPUT_MESSAGES


def collect_json_result(step_handler, item, command, filename, dir_path, json_result):
    json_result[step_handler.extract_entities_from_item(item)] = json_result.get(
        step_handler.extract_entities_from_item(item), []
    )
    result = command.to_json()
    result.update(
        {
            "filename": os.path.join(dir_path, get_file_parts(filename)),
            "absolute_file_path": filename,
        }
    )
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
