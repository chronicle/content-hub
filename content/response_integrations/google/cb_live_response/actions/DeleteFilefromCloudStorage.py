from __future__ import annotations
import json
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.ScriptResult import EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyDataModel import EntityTypes
from TIPCommon import extract_configuration_param, extract_action_param
from ..core.constants import DELETE_FILE_FROM_CLOUD_STORAGE, INTEGRATION_NAME
from ..core.Factory import ManagerFactory
from ..core.AsyncActionStepHandler import (
    ActionStep,
    FAILED_ENTITY_STATE,
    COMPLETED_ENTITY_STATE,
    IN_PROGRESS_ENTITY_STATE,
    ALL_FAILED_MSG,
    SOME_COMPLETED_MSG,
    SOME_FAILED_MSG,
)
from ..core.utils import get_entity_original_identifier
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
DELETE_STORAGE_FILES_CHECKER = "delete_storage_files"

MULTIPLE_DEVICES = "multiple_devices"
DUPLICATED_DEVICES = "duplicated_devices"

ACTION_COMPLETE_OUTPUT_MESSAGES = {ALL_FAILED_MSG: "No files were deleted."}

FAILED_OUTPUT_MESSAGE = (
    "Action failed to delete file {filename} for the following entities: {entities}"
)
SUCCESSFUL_OUTPUT_MESSAGE = (
    "Successfully deleted file {filename} for the following entities: {entities}"
)


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = DELETE_FILE_FROM_CLOUD_STORAGE

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

    filename = extract_action_param(siemplify, param_name="File Name", print_value=True)
    executing_limit_per_entity = extract_action_param(
        siemplify,
        param_name="Check for active session x times",
        print_value=True,
        input_type=int,
        is_mandatory=True,
    )

    filenames = (
        [filename]
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
        if not use_new_api_version:
            raise Exception(
                "Action failed to start. This action is not supported in Carbon Black Live Response API v3, "
                "API v6 should be used to run this action"
            )

        if not filenames:
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
                method_name="initial_step_for_multiple_data",
                variables={
                    "suitable_entities": [
                        get_entity_original_identifier(entity)
                        for entity in sorted_suitable_entities
                    ],
                    "additional_entities": filenames,
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
                wait_before_retry=2,
                method_name="session_status_check_by_item",
                retry=executing_limit_per_entity,
                variables={"previous_step": SESSION_STARTER},
            ),
            4: ActionStep(
                step_id=DELETE_STORAGE_FILES_CHECKER,
                step_label="Delete Files from Cloud Storage",
                method_name="delete_storage_files",
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
            f"Failed to execute {DELETE_FILE_FROM_CLOUD_STORAGE} action! Error is {e}"
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


def delete_storage_files(step_handler, json_result):
    for item in step_handler.get_entities_by_state(state=IN_PROGRESS_ENTITY_STATE):
        entity_identifier = step_handler.extract_entities_from_item(item)
        filename = step_handler.extract_entities_from_item(item, 1)
        session_id = step_handler.get_entity_data(item, SESSION_STARTER)
        step_handler.logger.info(f"Start process entity {entity_identifier}")
        try:
            files = step_handler.manager.get_storage_files_for_session(
                session_id=session_id
            )
            file_ids = []
            for file in files:
                if filename == file.filename:
                    file_ids.append(file.id)
            if file_ids:
                for file_id in file_ids:
                    step_handler.manager.delete_file_from_storage(
                        session_id=session_id, file_id=file_id
                    )
                step_handler.add_entity_data_to_step(item, file_ids)
                json_result = collect_json_result(
                    step_handler, item, filename, json_result
                )
            else:
                step_handler.fail_entity(
                    item,
                    reason=f"No files with file name {filename} found in Cloud Storage "
                    f"for session {session_id}",
                )
        except Exception as err:
            err_msg = f"An error occurred while getting data about storage files for session {session_id}. Error is {err}"
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


def collect_json_result(step_handler, item, filename, json_result):
    json_result[step_handler.extract_entities_from_item(item)] = json_result.get(
        step_handler.extract_entities_from_item(item), []
    )
    custom_json = {
        "step": "Delete Files from Cloud Storage",
        "is_success": True,
        "filename": filename,
    }
    json_result[step_handler.extract_entities_from_item(item)].append(custom_json)
    return json_result


if __name__ == "__main__":
    main()
