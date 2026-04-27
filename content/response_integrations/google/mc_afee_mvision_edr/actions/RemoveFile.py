from __future__ import annotations
import sys
import json

from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.ScriptResult import (
    EXECUTION_STATE_COMPLETED,
    EXECUTION_STATE_FAILED,
    EXECUTION_STATE_INPROGRESS,
)

from TIPCommon import extract_configuration_param, extract_action_param

from ..core.McAfeeMvisionEDRManager import McAfeeMvisionEDRManager
from ..core.constants import (
    PROVIDER_NAME,
    COMPLETED_STATUS,
    ERROR_STATUS,
    COMPLETED_ERROR_STATUS,
    IN_PROGRESS_STATUS,
)

SCRIPT_NAME = "McAfeeMvisionEDR - Remove File"


def find_in_host(entity, hosts):
    for host in hosts:
        if entity.identifier.lower() == host.hostname.lower() or entity.identifier in [
            item.ip for item in host.net_interfaces
        ]:
            return host.ma_guid
    return None


def start_operation(siemplify, manager, full_file_path):
    """
    Main RemoveFile action
    :param siemplify: SiemplifyAction object
    :param manager: McAfeeMvisionEDRManager object
    :param full_file_path: The full path to the file need to be removed.
    :return: {output message, json result, execution state}
    """
    entities_to_process = []
    output_message = ""
    suitable_entities = [
        entity
        for entity in siemplify.target_entities
        if entity.entity_type == EntityTypes.ADDRESS
        or entity.entity_type == EntityTypes.HOSTNAME
    ]

    not_found_entities = []
    duplicate_entities = []
    matched_entities = []

    try:
        hosts = manager.get_hosts()
        for entity in suitable_entities:
            siemplify.LOGGER.info(f"Started processing entity: {entity.identifier}")
            host_id = find_in_host(entity, hosts)
            if not host_id:
                not_found_entities.append(entity.identifier)
            else:
                if entity not in matched_entities:
                    matched_entities.append(entity)
                    entities_to_process.append(
                        {"entity": entity.identifier, "host_id": host_id}
                    )
                else:
                    duplicate_entities.append(entity.identifier)

    except Exception as e:
        err_msg = f"An error occurred performing action {SCRIPT_NAME}"
        siemplify.LOGGER.error(err_msg)
        siemplify.LOGGER.exception(e)

    if not_found_entities:
        output_message += (
            "\n\nAction was not able to find matching McAfee Mvision EDR endpoints for the following "
            "entities: {}".format(
                "\n".join([not_found for not_found in not_found_entities])
            )
        )

    if duplicate_entities:
        output_message += (
            "\n\nMultiple matches were found in McAfee Mvision EDR, taking first match for the "
            "following entities: {}".format(
                "\n".join([duplicate_entity for duplicate_entity in duplicate_entities])
            )
        )

    if entities_to_process:
        output_message += "\n\nStarted processing entities: {}".format(
            "\n".join(
                [matched_entity.identifier for matched_entity in matched_entities]
            )
        )
        return (
            output_message,
            json.dumps(
                (
                    [],
                    entities_to_process,
                    [],
                    [],
                    {},
                    not_found_entities,
                    duplicate_entities,
                )
            ),
            EXECUTION_STATE_INPROGRESS,
        )

    output_message = f"File {full_file_path} wasn't removed from any entities."
    return output_message, "false", EXECUTION_STATE_COMPLETED


def query_operation_status(
    siemplify,
    manager,
    processed_entities,
    entities_to_process,
    failed_entities,
    failed_entities_with_reason,
    current_entity,
    not_found_entities,
    duplicate_entities,
    full_file_path,
    safe_removal,
):
    """
    Main RemoveFile action
    :param siemplify: SiemplifyAction object
    :param manager: McAfeeMvisionEDRManager object
    :param processed_entities: list of processed entities
    :param entities_to_process: list of entities not processed
    :param failed_entities: list of failed entities
    :param failed_entities_with_reason: list of failed entities with reason
    :param current_entity: the entity currently being processed
    :param full_file_path: path to the file to be removed
    :param safe_removal: if enabled, will ignore files that may be critical or trusted.
    :return: {output message, json result, execution state}
    """
    result_value = "false"

    if not current_entity:
        current_entity = process_next_entity(
            siemplify, entities_to_process, manager, full_file_path, safe_removal
        )

    action_status = get_status(
        manager, current_entity.get("task_id"), get_error=False
    ).status

    if action_status == IN_PROGRESS_STATUS:
        output_message = (
            f"Continuing... processing entity: {current_entity.get('entity')}"
        )
        return (
            output_message,
            json.dumps(
                (
                    processed_entities,
                    entities_to_process,
                    failed_entities,
                    failed_entities_with_reason,
                    current_entity,
                    not_found_entities,
                    duplicate_entities,
                )
            ),
            EXECUTION_STATE_INPROGRESS,
        )

    output_message = ""
    if action_status == COMPLETED_STATUS:
        result_value = "true"
        processed_entities.append(current_entity.get("entity"))
        output_message = f"Successfully removed {full_file_path} from the following entity: {current_entity.get('entity')}"
    elif action_status == ERROR_STATUS:
        failed_entities.append(current_entity.get("entity"))
        output_message = f"Action wasn't able to remove file {full_file_path} from the following entity: {current_entity.get('entity')}"
    elif action_status == COMPLETED_ERROR_STATUS:
        errors = get_status(manager, current_entity.get("task_id"), get_error=True)
        fail_entity = {"entity": current_entity.get("entity")}
        if errors.descriptions:
            fail_entity["reason"] = "\n".join([err.desc for err in errors.descriptions])
        failed_entities_with_reason.append(fail_entity)
        output_message = f"Action wasn't able to remove file {full_file_path} from {fail_entity.get('entity')}."
        if errors.descriptions:
            output_message += f" Reason: {fail_entity.get('reason')}"

    if entities_to_process:
        current_entity = process_next_entity(
            siemplify, entities_to_process, manager, full_file_path, safe_removal
        )
        return (
            output_message,
            json.dumps(
                (
                    processed_entities,
                    entities_to_process,
                    failed_entities,
                    failed_entities_with_reason,
                    current_entity,
                    not_found_entities,
                    duplicate_entities,
                )
            ),
            EXECUTION_STATE_INPROGRESS,
        )

    output_message = ""
    if processed_entities:
        result_value = "true"
        output_message += (
            "Successfully removed {} from the following entities: {}".format(
                full_file_path,
                "\n".join(
                    [processed_entity for processed_entity in processed_entities]
                ),
            )
        )

    if failed_entities:
        output_message += "\n\nAction wasn't able to remove file {} from the following entities: {}".format(
            full_file_path,
            "\n".join([failed_entity for failed_entity in failed_entities]),
        )

    if failed_entities_with_reason:
        for item in failed_entities_with_reason:
            output_message += f"\n\nAction wasn't able to remove file {full_file_path} from {item.get('entity')}."
            if item.get("reason"):
                output_message += f" Reason: {item.get('reason')}"

    if not_found_entities:
        output_message += (
            "\n\nAction was not able to find matching McAfee Mvision EDR endpoints for the following "
            "entities: {}".format(
                "\n".join([not_found for not_found in not_found_entities])
            )
        )

    if duplicate_entities:
        output_message += (
            "\n\nMultiple matches were found in McAfee Mvision EDR, taking first match for the "
            "following entities: {}".format(
                "\n".join([duplicate_entity for duplicate_entity in duplicate_entities])
            )
        )

    return output_message, result_value, EXECUTION_STATE_COMPLETED


def process_next_entity(siemplify, entities_to_process, manager, path, safe_removal):
    """
    Get next entity in queue
    :param entities_to_process: entities to be processed
    :param manager: McAfeeMvisionEDRManager object
    :param path: path to the file to be removed
    :param safe_removal: if enabled, will ignore files that may be critical or trusted.
    :return: new_entity_to_process
    """
    try:
        new_entity_to_process = entities_to_process.pop(0)
        host_id = new_entity_to_process.get("host_id")
        task_id = manager.remove_file(host_id, path, safe_removal).status_id
        new_entity_to_process["task_id"] = task_id
        return new_entity_to_process
    except Exception as e:
        siemplify.LOGGER.error(f"General error performing action {SCRIPT_NAME}")
        siemplify.LOGGER.exception(e)
        return None


def get_status(manager, action_id, get_error):
    """
    Get action status
    :param manager: McAfeeMvisionEDRManager object
    :param action_id: created task status id
    :param get_error: defines if the error message should be retrieved
    :return: {status of the action}
    """
    return manager.get_action_status(action_id, get_error)


@output_handler
def main(is_first_run):
    siemplify = SiemplifyAction()
    siemplify.script_name = SCRIPT_NAME
    mode = "Main" if is_first_run else "QueryState"

    siemplify.LOGGER.info(f"----------------- {mode} - Param Init -----------------")

    # Configuration.
    api_root = extract_configuration_param(
        siemplify, provider_name=PROVIDER_NAME, param_name="API Root", input_type=str
    )
    login_api_root = extract_configuration_param(
        siemplify,
        provider_name=PROVIDER_NAME,
        param_name="Login API Root",
        input_type=str,
    )
    username = extract_configuration_param(
        siemplify, provider_name=PROVIDER_NAME, param_name="Username", input_type=str
    )
    password = extract_configuration_param(
        siemplify, provider_name=PROVIDER_NAME, param_name="Password", input_type=str
    )
    client_id = extract_configuration_param(
        siemplify, provider_name=PROVIDER_NAME, param_name="Client ID", input_type=str
    )
    client_secret = extract_configuration_param(
        siemplify,
        provider_name=PROVIDER_NAME,
        param_name="Client Secret",
        input_type=str,
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=PROVIDER_NAME,
        param_name="Verify SSL",
        default_value=False,
        input_type=bool,
    )

    # Parameters
    file_full_path = extract_action_param(
        siemplify, param_name="Full File Path", is_mandatory=True, input_type=str
    )
    safe_removal = extract_action_param(
        siemplify,
        param_name="Safe Removal",
        is_mandatory=True,
        input_type=bool,
        default_value=True,
    )

    siemplify.LOGGER.info(f"----------------- {mode} - Started -----------------")

    try:
        mvision_edr_manager = McAfeeMvisionEDRManager(
            api_root,
            username,
            password,
            client_id,
            client_secret,
            verify_ssl=verify_ssl,
            login_api_root=login_api_root,
        )

        if is_first_run:
            output_message, result_value, status = start_operation(
                siemplify, mvision_edr_manager, file_full_path
            )
        else:
            (
                processed_entities,
                entities_to_process,
                failed_entities,
                failed_entities_with_reason,
                current_entity,
                not_found_entities,
                duplicate_entities,
            ) = json.loads(siemplify.parameters["additional_data"])
            output_message, result_value, status = query_operation_status(
                siemplify,
                mvision_edr_manager,
                processed_entities,
                entities_to_process,
                failed_entities,
                failed_entities_with_reason,
                current_entity,
                not_found_entities,
                duplicate_entities,
                file_full_path,
                safe_removal,
            )

    except Exception as e:
        siemplify.LOGGER.error(f"General error performing action {SCRIPT_NAME}")
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        result_value = "false"
        output_message = f"Error executing action {SCRIPT_NAME}. Reason: {e}"

    siemplify.LOGGER.info(f"----------------- {mode} - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  result_value: {result_value}\n  output_message: {output_message}"
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    is_first_run = len(sys.argv) < 3 or sys.argv[2] == "True"
    main(is_first_run)
