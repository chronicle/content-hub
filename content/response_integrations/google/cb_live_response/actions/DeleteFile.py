from __future__ import annotations
import os
import json
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.ScriptResult import EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyDataModel import EntityTypes
from TIPCommon import extract_configuration_param, extract_action_param
from ..core.constants import DELETE_FILE_SCRIPT_NAME, INTEGRATION_NAME
from ..core.Factory import ManagerFactory
from ..core.AsyncActionStepHandler import (
    ActionStep,
    FAILED_ENTITY_STATE,
    COMPLETED_ENTITY_STATE,
    IN_PROGRESS_ENTITY_STATE,
    IN_PROGRESS_MSG,
    ALL_FAILED_MSG,
    SOME_COMPLETED_MSG,
    SOME_FAILED_MSG,
    ENTITY_KEY_FOR_FORMAT,
    ENTITY_FILENAME_CONCAT_CHAR,
)
from ..core.utils import get_entity_original_identifier, string_to_multi_value
from ..core.CBLiveResponseActionSteps import (
    device_custom_output_messages,
    format_output_message,
)
from ..core.AsyncActionStepHandlerMultiple import AsyncActionStepHandlerMultiple

SUPPORTED_ENTITY_TYPES = [EntityTypes.ADDRESS, EntityTypes.HOSTNAME]

INITIAL_STEP = "initial_step"
DEVICE_GETTER = "device"
SESSION_STARTER = "session_starter"
SESSION_CHECKER = "session_status"
COMMAND_STARTER = "command"
COMMAND_CHECKER = "command_object"
MULTIPLE_DEVICES = "multiple_devices"
DUPLICATED_DEVICES = "duplicated_devices"

ACTION_COMPLETE_OUTPUT_MESSAGES = {
    IN_PROGRESS_MSG: f"Action reached timeout waiting for results for the following entities: {{{ENTITY_KEY_FOR_FORMAT}}}",
    ALL_FAILED_MSG: "No files were deleted.",
}

SUCCESSFUL_OUTPUT_MESSAGE = (
    "Successfully deleted file {filename} for the following entities: {entities}"
)
FAILED_OUTPUT_MESSAGE = (
    "Action failed to delete file {filename} for the following entities: {entities}"
)


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = DELETE_FILE_SCRIPT_NAME

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

    file_name = string_to_multi_value(
        extract_action_param(siemplify, param_name="File Name", print_value=True)
    )
    remote_file_path = string_to_multi_value(
        extract_action_param(
            siemplify, param_name="Remote Directory Path", print_value=True
        )
    )
    executing_limit_per_entity = extract_action_param(
        siemplify,
        param_name="Check for active session x times",
        print_value=True,
        input_type=int,
        is_mandatory=True,
    )

    file_names = (
        file_name
        if file_name
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
    ACTION_COMPLETE_OUTPUT_MESSAGES[SOME_COMPLETED_MSG] = (
        f"Successfully deleted file {file_name} for the following entities: "
        + f"{{{ENTITY_KEY_FOR_FORMAT}}}"
    )
    ACTION_COMPLETE_OUTPUT_MESSAGES[SOME_FAILED_MSG] = (
        f"Action failed to delete file {file_name} for the following entities: "
        + f"{{{ENTITY_KEY_FOR_FORMAT}}}"
    )
    try:
        if not remote_file_path:
            if not file_names:
                raise Exception(
                    "Action failed to start since both Filename Remote Directory Path were not provided."
                )
            if not is_all_filenames_with_folders(file_names):
                raise Exception(
                    "Action failed to start since some of the elements specified as a placeholder for the "
                    "File Name are full path, and some are not."
                )

        if remote_file_path:
            if not file_names:
                raise Exception(
                    "Action failed to start since both Filename Remote Directory Path were not provided."
                )
            if not is_all_filenames_without_folders(file_names):
                raise Exception(
                    "Action failed to start since some of the elements specified as a placeholder for the "
                    "File Name are full path, and some are not."
                )

        if remote_file_path and file_names:
            if len(file_names) != len(remote_file_path):
                raise Exception(
                    "Action failed to start since the number of elements specified in File Name and Remote "
                    "Directory Path action input parameters are different"
                )

        if not file_names:
            raise Exception(
                "Action failed to start since Filename was not provided either as Siemplify Entity or "
                "action input parameter."
            )

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
                    "filenames": file_names,
                    "directory_paths": remote_file_path,
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
                step_id=COMMAND_STARTER,
                step_label="Command Start",
                method_name="command_start",
            ),
            5: ActionStep(
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
            f"Failed to execute {DELETE_FILE_SCRIPT_NAME} action! Error is {e}"
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


def initial_step(step_handler, suitable_entities, filenames, directory_paths):
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


def command_start(step_handler):
    for item in step_handler.get_entities_by_state(state=IN_PROGRESS_ENTITY_STATE):
        entity_identifier = step_handler.extract_entities_from_item(item)
        filename = step_handler.extract_entities_from_item(item, 1)
        session_id = step_handler.get_entity_data(item, SESSION_STARTER)
        step_handler.logger.info(f"Start processing entity {entity_identifier}")
        try:
            command = step_handler.manager.start_command_for_delete_file(
                session_id=session_id, remote_file_path=filename
            )
            step_handler.add_entity_data_to_step(item, command.id)
        except Exception as err:
            err_msg = f"An error occurred while getting data about command for session {session_id}. Error is {err}"
            step_handler.logger.error(err_msg)
            step_handler.logger.exception(err)
            step_handler.fail_entity(item, reason=err_msg)
        step_handler.logger.info(f"Finishing processing entity {entity_identifier}")


def command_check(step_handler, json_result):
    for item in step_handler.get_entities_by_state(state=IN_PROGRESS_ENTITY_STATE):
        entity_identifier = step_handler.extract_entities_from_item(item)
        filename = step_handler.extract_entities_from_item(item, 1)
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
                        step_handler, item, command, filename, json_result
                    )
                    step_handler.add_entity_data_to_step(item, command)
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
    step_handler.add_output_messages(get_output_message(step_handler))
    add_custom_output_messages(step_handler)


def add_custom_output_messages(step_handler):
    message = device_custom_output_messages(step_handler)

    if message:
        step_handler.add_addition_output_message(message)


def get_output_message(step_handler):
    ACTION_COMPLETE_OUTPUT_MESSAGES.update(
        {
            SOME_COMPLETED_MSG: format_output_message(
                step_handler, SUCCESSFUL_OUTPUT_MESSAGE, COMPLETED_ENTITY_STATE
            ),
            SOME_FAILED_MSG: format_output_message(
                step_handler, FAILED_OUTPUT_MESSAGE, FAILED_ENTITY_STATE
            ),
        }
    )
    return ACTION_COMPLETE_OUTPUT_MESSAGES


def collect_json_result(step_handler, item, command, filename, json_result):
    json_result[step_handler.extract_entities_from_item(item)] = json_result.get(
        step_handler.extract_entities_from_item(item), []
    )
    result = command.to_json()
    result.update({"filename": filename})
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


if __name__ == "__main__":
    main()
