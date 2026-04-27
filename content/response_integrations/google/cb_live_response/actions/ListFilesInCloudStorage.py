from __future__ import annotations
import json
from soar_sdk.SiemplifyUtils import output_handler, construct_csv
from soar_sdk.ScriptResult import EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyDataModel import EntityTypes
from TIPCommon import extract_configuration_param, extract_action_param
from ..core.constants import (
    LIST_FILES_SCRIPT_NAME,
    INTEGRATION_NAME,
    VENDOR_NAME,
    SHORT_VENDOR_NAME,
    STORAGE_FILES_CASE_WALL,
)
from ..core.Factory import ManagerFactory
from ..core.AsyncActionStepHandler import (
    AsyncActionStepHandler,
    ActionStep,
    IN_PROGRESS_ENTITY_STATE,
    IN_PROGRESS_MSG,
    ALL_FAILED_MSG,
    SOME_COMPLETED_MSG,
    SOME_FAILED_MSG,
    ENTITY_KEY_FOR_FORMAT,
)
from ..core.utils import get_entity_original_identifier, get_validated_limit

SUPPORTED_ENTITY_TYPES = [EntityTypes.ADDRESS, EntityTypes.HOSTNAME]

INITIAL_STEP = "initial_step"
DEVICE_GETTER = "device"
SESSION_STARTER = "session_starter"
SESSION_CHECKER = "session_status"
STORAGE_FILES_CHECKER = "get_storage_files"
MULTIPLE_DEVICES = "multiple_devices"
DUPLICATED_DEVICES = "duplicated_devices"

ACTION_COMPLETE_OUTPUT_MESSAGES = {
    IN_PROGRESS_MSG: f"Action reached timeout waiting for results for the following entities: {{{ENTITY_KEY_FOR_FORMAT}}}",
    ALL_FAILED_MSG: f"No files were returned from {SHORT_VENDOR_NAME} file File Storage.",
    SOME_COMPLETED_MSG: f"{SHORT_VENDOR_NAME} File Storage file list successfully returned for the following entities: "
    f"{{{ENTITY_KEY_FOR_FORMAT}}}",
    SOME_FAILED_MSG: f"Action was not able to get {SHORT_VENDOR_NAME} File Storage file list for the following "
    f"entities: {{{ENTITY_KEY_FOR_FORMAT}}}",
}


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = LIST_FILES_SCRIPT_NAME

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

    max_rows_to_return = extract_action_param(
        siemplify, param_name="Max Rows to Return", print_value=True, input_type=int
    )
    start_from_row = extract_action_param(
        siemplify, param_name="Start from Row", print_value=True, input_type=int
    )
    executing_limit_per_entity = extract_action_param(
        siemplify,
        param_name="Check for active session x times",
        print_value=True,
        input_type=int,
        is_mandatory=True,
    )
    max_results = get_validated_limit(max_rows_to_return)

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
                    ]
                },
            ),
            1: ActionStep(
                step_id=DEVICE_GETTER,
                step_label="Get Corresponding CB Cloud Device",
                method_name="get_device_id",
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
                method_name="session_status_check",
                retry=executing_limit_per_entity,
                wait_before_retry=2,
                variables={"previous_step": SESSION_STARTER},
            ),
            4: ActionStep(
                step_id=STORAGE_FILES_CHECKER,
                step_label="Get Files from Cloud Storage",
                method_name="get_storage_files",
                variables={
                    "json_result": json_result,
                    "start_from": start_from_row,
                    "max_results": max_results,
                },
            ),
        }
        result_value = json.loads(
            extract_action_param(
                siemplify, param_name="additional_data", default_value="{}"
            )
        )
        step_handler = AsyncActionStepHandler(
            siemplify, manager, action_steps, result_value, globals()
        )
        output_message, result_value, status = step_handler.execute_steps()
        if isinstance(result_value, dict):
            result_value = json.dumps(result_value)

    except Exception as e:
        output_message = (
            f"Failed to execute {LIST_FILES_SCRIPT_NAME} action! Error is {e}"
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


def get_storage_files(step_handler, json_result, start_from, max_results):
    step_handler.add_output_messages(ACTION_COMPLETE_OUTPUT_MESSAGES)
    for entity in step_handler.get_entities_by_state(state=IN_PROGRESS_ENTITY_STATE):
        step_handler.logger.info(f"Start process entity {entity}")
        session_id = step_handler.get_entity_data(entity, SESSION_STARTER)

        try:
            files = step_handler.manager.get_storage_files_for_session(
                session_id=session_id, start_from=start_from, limit=max_results
            )
            if files:
                add_case_wall_data(step_handler, files, session_id)
                json_result = collect_json_result(entity, files, json_result)
                step_handler.add_entity_data_to_step(entity, files)
            else:
                step_handler.fail_entity(
                    entity, reason="No files found in Cloud Storage"
                )
        except Exception as err:
            err_msg = f"An error occurred while getting data about storage files for session {session_id}."
            step_handler.logger.error(err_msg)
            step_handler.logger.exception(err)
            step_handler.fail_entity(entity, reason=err_msg)
        step_handler.logger.info(f"Finishing processing entity {entity}")

    add_custom_output_messages(step_handler)
    if json_result:
        step_handler.json_result = json_result


def add_custom_output_messages(step_handler):
    message = ""

    if step_handler.get_custom_variable(MULTIPLE_DEVICES):
        message += (
            f"Multiple matches were found in {VENDOR_NAME}, taking agent with the most recent last_contact_time"
            f" the following entities: {', '.join(step_handler.get_custom_variable(MULTIPLE_DEVICES))}\n"
        )

    if step_handler.get_custom_variable(DUPLICATED_DEVICES):
        message += (
            "Provided IP and Hostname entities reference the same CB agent, taking Hostname entity for the "
            "following Hostname:IP pairs: {}\n".format(
                ", ".join(
                    [
                        f"{item[0]} - {item[1]}"
                        for item in step_handler.get_custom_variable(DUPLICATED_DEVICES)
                    ]
                )
            )
        )

    if message:
        step_handler.add_addition_output_message(message)


def collect_json_result(entity, files, json_result):
    json_result[entity] = [file.to_json() for file in files]
    return json_result


def add_case_wall_data(step_handler, files, session_id):
    step_handler.siemplify.result.add_data_table(
        STORAGE_FILES_CASE_WALL.format(VENDOR_NAME, session_id),
        construct_csv([file.to_table() for file in files]),
    )


if __name__ == "__main__":
    main()
