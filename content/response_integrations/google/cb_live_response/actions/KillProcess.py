from __future__ import annotations
import json
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.ScriptResult import EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from TIPCommon import extract_configuration_param, extract_action_param
from ..core.utils import get_entity_original_identifier
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
from ..core.constants import KILL_PROCESS_SCRIPT_NAME, INTEGRATION_NAME, VENDOR_NAME

SUPPORTED_ENTITY_TYPES = [EntityTypes.ADDRESS, EntityTypes.HOSTNAME]
ACTION_COMPLETE_OUTPUT_MESSAGES = {
    IN_PROGRESS_MSG: f"Action reached timeout waiting for results for the following entities: {{{ENTITY_KEY_FOR_FORMAT}}}",
    ALL_FAILED_MSG: "Action was not able to kill process {} for the following entities: {}",
    SOME_COMPLETED_MSG: f"Successfully killed process for the following entities: {{{ENTITY_KEY_FOR_FORMAT}}}",
    SOME_FAILED_MSG: "Action was not able to kill process {} for the following entities: {}",
}

INITIAL_STEP = "initial_step"
DEVICE_GETTER = "device"
SESSION_STARTER = "session_starter"
SESSION_CHECKER = "session_status"
LIST_PROCESSES_COMMAND_STARTER = "list_processes_command"
LIST_PROCESSES_COMMAND_CHECKER = "list_processes_command_object"
KILL_PROCESS_COMMAND_STARTER = "kill_process_command"
KILL_PROCESS_COMMAND_CHECKER = "kill_process_command_object"

MULTIPLE_DEVICES = "multiple_devices"
DUPLICATED_DEVICES = "duplicated_devices"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = KILL_PROCESS_SCRIPT_NAME

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

    process_name = extract_action_param(
        siemplify, param_name="Process Name", print_value=True
    )
    executing_limit_per_entity = extract_action_param(
        siemplify,
        param_name="Check for active session x times",
        print_value=True,
        is_mandatory=True,
        input_type=int,
    )

    if not process_name:
        siemplify.LOGGER.info(
            "No process name was given as a parameter. Looking for PROCESS artifact to use as process name."
        )
        process_artifacts = [
            entity
            for entity in siemplify.target_entities
            if entity.entity_type == EntityTypes.PROCESS
        ]

        if not process_artifacts:
            output_message = "Process name or process artifact must be provided."
            siemplify.LOGGER.error(output_message)
            siemplify.end(output_message, False, EXECUTION_STATE_FAILED)

        process_name = process_artifacts[
            0
        ].identifier  # Take the name of process artifact
        siemplify.LOGGER.info(f"Found PROCESS artifact: {process_name}.")

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
    ACTION_COMPLETE_OUTPUT_MESSAGES[SOME_FAILED_MSG] = (
        f"Action was not able to kill process {process_name} for the following entities: "
        + f"{{{ENTITY_KEY_FOR_FORMAT}}}"
    )
    ACTION_COMPLETE_OUTPUT_MESSAGES[ALL_FAILED_MSG] = ACTION_COMPLETE_OUTPUT_MESSAGES[
        SOME_FAILED_MSG
    ]
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
                step_label="Get Device",
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
                step_id=LIST_PROCESSES_COMMAND_STARTER,
                step_label="List Processes Command Start",
                method_name="list_processes_command_start",
            ),
            5: ActionStep(
                step_id=LIST_PROCESSES_COMMAND_CHECKER,
                step_label="List Processes Command Check",
                method_name="list_processes_command_check",
                retry=5,
                wait_before_retry=30,
                variables={"process_name": process_name},
            ),
            6: ActionStep(
                step_id=KILL_PROCESS_COMMAND_STARTER,
                step_label="Kill Process Command Start",
                method_name="kill_process_command_start",
                variables={"process_name": process_name},
            ),
            7: ActionStep(
                step_id=KILL_PROCESS_COMMAND_CHECKER,
                step_label="Kill Process Command Check",
                method_name="kill_process_command_check",
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
        step_handler = AsyncActionStepHandler(
            siemplify, manager, action_steps, result_value, globals()
        )
        output_message, result_value, status = step_handler.execute_steps()
        if isinstance(result_value, dict):
            result_value = json.dumps(result_value)

    except Exception as e:
        output_message = (
            f"Failed to execute {KILL_PROCESS_SCRIPT_NAME} action! Error is {e}"
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


def list_processes_command_start(step_handler):
    step_handler.add_output_messages(
        {
            SOME_FAILED_MSG: f"Action was not able to get process list for the following entities: "
            f"\n{{{ENTITY_KEY_FOR_FORMAT}}}"
        }
    )
    for entity in step_handler.get_entities_by_state(state=IN_PROGRESS_ENTITY_STATE):
        step_handler.logger.info(f"Start processing entity {entity}")
        session_id = step_handler.get_entity_data(entity, SESSION_STARTER)

        try:
            step_handler.logger.info(f"Starting command for list files")
            command = step_handler.manager.start_command_for_process_list(
                session_id=session_id
            )
            step_handler.add_entity_data_to_step(entity, command.id)
        except Exception as err:
            err_msg = f"An error occurred while getting data about command for session {session_id}. Error is {err}"
            step_handler.logger.error(err_msg)
            step_handler.logger.exception(err)
            step_handler.fail_entity(entity, reason=err_msg)
        step_handler.logger.info(f"Finishing processing entity {entity}")


def list_processes_command_check(step_handler, process_name):
    in_progress_entities = step_handler.get_entities_by_state(
        state=IN_PROGRESS_ENTITY_STATE
    ).copy()
    failed_entities = []
    no_results_entities = []
    for entity in in_progress_entities:
        step_handler.logger.info(f"Start process entity {entity}")
        session_id = step_handler.get_entity_data(entity, SESSION_STARTER)
        command_id = step_handler.get_entity_data(
            entity, LIST_PROCESSES_COMMAND_STARTER
        )

        try:
            step_handler.logger.info(f"Getting command")
            command = step_handler.manager.get_process_command_by_id(
                session_id=session_id, command_id=command_id, process_name=process_name
            )
            if command.is_completed:
                step_handler.logger.info(f"Command is ready.")
                processes = command.processes
                if processes:
                    step_handler.add_entity_data_to_step(entity, processes[0].pid)
                else:
                    err_msg = f"No matching processes were found for {entity}."
                    step_handler.logger.info(err_msg)
                    step_handler.fail_entity(entity, reason=err_msg)
                    no_results_entities.append(entity)
        except Exception as err:
            err_msg = (
                f"An error occurred while getting data about command {command_id} for session {session_id}."
                f" Error is {err}"
            )
            step_handler.logger.error(err_msg)
            step_handler.logger.exception(err)
            step_handler.fail_entity(entity, reason=err_msg)
            failed_entities.append(entity)
        step_handler.logger.info(f"Finishing processing entity {entity}")
    failed_output_message = ""
    if no_results_entities:
        failed_output_message += (
            f"No matching processes were found on the following entities: "
            f"{', '.join(no_results_entities)}"
        )
    if failed_entities:
        failed_output_message += (
            f"Action was not able to find process ID for the following entities: "
            f"{', '.join(failed_entities)}"
        )
    step_handler.add_output_messages({SOME_FAILED_MSG: failed_output_message})

    add_custom_output_messages(step_handler)


def kill_process_command_start(step_handler, process_name):
    step_handler.add_output_messages(
        {
            SOME_FAILED_MSG: f"Action was not able to kill process {process_name} for the following entities: {{{ENTITY_KEY_FOR_FORMAT}}}"
        }
    )
    for entity in step_handler.get_entities_by_state(state=IN_PROGRESS_ENTITY_STATE):
        step_handler.logger.info(f"Start processing entity {entity}")
        session_id = step_handler.get_entity_data(entity, SESSION_STARTER)
        process_pid = step_handler.get_entity_data(
            entity, LIST_PROCESSES_COMMAND_CHECKER
        )
        try:
            command = step_handler.manager.initiate_kill_process_command(
                session_id=session_id, pid=process_pid
            )
            step_handler.add_entity_data_to_step(entity, command.id)
        except Exception as err:
            err_msg = f"An error occurred while getting data about command for session {session_id}. Error is {err}"
            step_handler.logger.error(err_msg)
            step_handler.logger.exception(err)
            step_handler.fail_entity(entity, reason=err_msg)
        step_handler.logger.info(f"Finishing processing entity {entity}")


def kill_process_command_check(step_handler, json_result):
    step_handler.add_output_messages(ACTION_COMPLETE_OUTPUT_MESSAGES)
    for entity in step_handler.get_entities_by_state(state=IN_PROGRESS_ENTITY_STATE):
        step_handler.logger.info(f"Start process entity {entity}")
        session_id = step_handler.get_entity_data(entity, SESSION_STARTER)
        command_id = step_handler.get_entity_data(entity, KILL_PROCESS_COMMAND_STARTER)

        try:
            step_handler.logger.info(f"Getting command")
            command = step_handler.manager.get_kill_process_command_by_id(
                session_id=session_id, command_id=command_id
            )
            if command.is_completed or command.is_failed:
                step_handler.logger.info(f"Command is ready.")
                json_result = collect_json_result(entity, command, json_result)
                if command.is_completed:
                    step_handler.add_entity_data_to_step(entity, command)
                else:
                    err_msg = "Command status is ERROR"
                    step_handler.fail_entity(entity, reason=err_msg)
        except Exception as err:
            err_msg = (
                f"An error occurred while getting data about command {command_id} for session {session_id}."
                f" Error is {err}"
            )
            step_handler.logger.error(err_msg)
            step_handler.logger.exception(err)
            step_handler.fail_entity(entity, reason=err_msg)
        step_handler.logger.info(f"Finishing processing entity {entity}")
    add_custom_output_messages(step_handler)
    if json_result:
        step_handler.json_result = json_result


def collect_json_result(entity, command, json_result):
    json_result[entity] = command.to_json()

    return json_result


def add_custom_output_messages(step_handler):
    message = ""
    if step_handler.get_custom_variable(MULTIPLE_DEVICES):
        message += (
            f"Multiple matches were found in {VENDOR_NAME}, taking agent with the most recent last_contact_time "
            f"the following entities: {', '.join(step_handler.get_custom_variable(MULTIPLE_DEVICES))}\n"
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


if __name__ == "__main__":
    main()
