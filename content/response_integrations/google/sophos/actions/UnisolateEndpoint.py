from __future__ import annotations
import json
import sys
from ..core.SophosManager import SophosManager
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.ScriptResult import (
    EXECUTION_STATE_COMPLETED,
    EXECUTION_STATE_FAILED,
    EXECUTION_STATE_INPROGRESS,
)
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler, unix_now
from TIPCommon import extract_configuration_param, extract_action_param
from ..core.constants import (
    INTEGRATION_NAME,
    INTEGRATION_DISPLAY_NAME,
    UNISOLATE_ENDPOINT_SCRIPT_NAME,
    UNISOLATED,
    ISOLATED,
    ISOLATION_IN_PROGRESS,
    DEFAULT_TIMEOUT,
)
from ..core.utils import is_approaching_timeout, is_async_action_global_timeout_approaching

SUPPORTED_ENTITY_TYPES = [EntityTypes.ADDRESS, EntityTypes.HOSTNAME]


def start_operation(siemplify, manager, suitable_entities, comment):
    status = EXECUTION_STATE_INPROGRESS
    result_value = {
        "endpoint_ids": {},
        "target_entities": [],
        "successful": [],
        "already_completed": [],
        "pending": [],
        "failed": [],
    }

    if suitable_entities:
        for entity in suitable_entities:
            try:
                result_value["target_entities"].append(entity.identifier)
                endpoint = manager.find_entities(
                    entity_identifier=entity.identifier, entity_type=entity.entity_type
                )
                if not endpoint:
                    siemplify.LOGGER.info(
                        f"Endpoint was not found for entity {entity.identifier}. "
                        "Skipping."
                    )
                    result_value["failed"].append(entity.identifier)
                    continue
                result_value["endpoint_ids"][entity.identifier] = endpoint.scan_id
                initial_isolation_status = manager.check_isolation_status(
                    endpoint_id=endpoint.scan_id
                )
                if initial_isolation_status == ISOLATED:
                    manager.isolate_or_unisolate_endpoint(
                        isolate=False, endpoint_id=endpoint.scan_id, comment=comment
                    )
                    final_isolation_status = manager.check_isolation_status(
                        endpoint_id=endpoint.scan_id
                    )
                    if final_isolation_status == UNISOLATED:
                        result_value["successful"].append(entity.identifier)
                    else:
                        result_value["pending"].append(entity.identifier)
                elif initial_isolation_status == UNISOLATED:
                    siemplify.LOGGER.info(
                        f"Endpoint for entity {entity.identifier} is already "
                        "unisolated. Skipping."
                    )
                    result_value["already_completed"].append(entity.identifier)
                elif initial_isolation_status == ISOLATION_IN_PROGRESS:
                    result_value["pending"].append(entity.identifier)

            except Exception as e:
                result_value["failed"].append(entity.identifier)
                siemplify.LOGGER.error(
                    f"An error occurred on entity {entity.identifier}"
                )
                siemplify.LOGGER.exception(e)

    if result_value["pending"]:
        output_message = (
            "Waiting for unisolation to finish on the following entities: "
            "{}".format(", ".join(result_value["pending"]))
        )
        result_value = json.dumps(result_value)
        return output_message, result_value, status

    output_message, result_value, status = finish_operation(
        siemplify=siemplify, result_data=result_value, timeout_approaching=False
    )

    return output_message, result_value, status


def query_operation_status(siemplify, manager, action_start_time, result_data):
    timeout_approaching = False

    for entity_id in list(result_data["endpoint_ids"].keys()):
        if entity_id not in result_data["pending"]:
            result_data["endpoint_ids"].pop(entity_id, None)

    if is_async_action_global_timeout_approaching(
        siemplify, action_start_time
    ) or is_approaching_timeout(action_start_time, DEFAULT_TIMEOUT):
        siemplify.LOGGER.info("Timeout is approaching. Action will gracefully exit")
        timeout_approaching = True
    else:
        for identifier, endpoint_id in list(result_data["endpoint_ids"].items()):
            final_isolation_status = manager.check_isolation_status(
                endpoint_id=endpoint_id
            )
            if final_isolation_status == UNISOLATED:
                result_data["successful"].append(identifier)
                if identifier in result_data["pending"]:
                    result_data["pending"].remove(identifier)

        if result_data["pending"]:
            output_message = (
                "Waiting for unisolation to finish on the following entities: "
                "{}".format(", ".join(result_data["pending"]))
            )
            result_value = json.dumps(result_data)
            return output_message, result_value, EXECUTION_STATE_INPROGRESS

    output_message, result_value, status = finish_operation(
        siemplify=siemplify,
        result_data=result_data,
        timeout_approaching=timeout_approaching,
    )

    return output_message, result_value, status


def finish_operation(siemplify, result_data, timeout_approaching):
    result_value = True
    status = EXECUTION_STATE_COMPLETED
    output_message = ""
    successful_entities = []
    already_completed = []
    failed_entities = []
    pending_entities = []

    for entity in result_data["target_entities"]:
        if entity in result_data["successful"]:
            successful_entities.append(entity)
        elif entity in result_data["already_completed"]:
            already_completed.append(entity)
        elif entity in result_data["failed"]:
            failed_entities.append(entity)
        else:
            pending_entities.append(entity)

    if successful_entities:
        output_message += (
            "Successfully unisolated the following endpoints in {}: "
            "{}\n".format(
                INTEGRATION_DISPLAY_NAME,
                ", ".join([entity for entity in successful_entities]),
            )
        )

    if already_completed:
        output_message += (
            "The following endpoints were already unisolated in {}: "
            "{}\n".format(
                INTEGRATION_DISPLAY_NAME,
                ", ".join([entity for entity in already_completed]),
            )
        )

    if failed_entities:
        output_message += "The following entities were not found in {}: " "{}\n".format(
            INTEGRATION_DISPLAY_NAME, ", ".join([entity for entity in failed_entities])
        )

    if timeout_approaching and pending_entities:
        err = f"action ran into a timeout. Pending entities: {', '.join([entity for entity in pending_entities])}\nPlease increase the timeout in IDE."
        error_message = (
            f"Error executing action {UNISOLATE_ENDPOINT_SCRIPT_NAME}. Reason: {err}"
        )
        siemplify.LOGGER.error(error_message)
        output_message = f"{error_message}\n{output_message}"
        result_value = False
        status = EXECUTION_STATE_FAILED

        return output_message, result_value, status

    if not successful_entities and not already_completed:
        result_value = False
        if not failed_entities:
            output_message = "No supported entities were found in the scope."
        else:
            output_message = (
                "None of the provided entities were found in "
                f"{INTEGRATION_DISPLAY_NAME}."
            )
    return output_message, result_value, status


@output_handler
def main(is_first_run):
    siemplify = SiemplifyAction()
    action_start_time = unix_now()
    siemplify.script_name = UNISOLATE_ENDPOINT_SCRIPT_NAME
    mode = "Main" if is_first_run else "Isolate Endpoint"
    siemplify.LOGGER.info(f"----------------- {mode} - Param Init -----------------")

    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Root",
        is_mandatory=True,
        input_type=str,
    )
    client_id = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Client ID",
        is_mandatory=True,
        input_type=str,
    )
    client_secret = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Client Secret",
        is_mandatory=True,
        input_type=str,
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        default_value=False,
        input_type=bool,
    )

    # Action parameters
    comment = extract_action_param(
        siemplify,
        param_name="Comment",
        is_mandatory=True,
        print_value=True,
        input_type=str,
    )

    siemplify.LOGGER.info(f"----------------- {mode} - Started -----------------")

    output_message = ""
    status = EXECUTION_STATE_INPROGRESS
    result_value = False
    suitable_entities = [
        entity
        for entity in siemplify.target_entities
        if entity.entity_type in SUPPORTED_ENTITY_TYPES
    ]

    try:
        manager = SophosManager(
            api_root=api_root,
            client_id=client_id,
            client_secret=client_secret,
            verify_ssl=verify_ssl,
            test_connectivity=True,
        )

        if is_first_run:
            output_message, result_value, status = start_operation(
                siemplify,
                manager=manager,
                suitable_entities=suitable_entities,
                comment=comment,
            )
        if status == EXECUTION_STATE_INPROGRESS:
            result_data = (
                result_value
                if result_value
                else extract_action_param(
                    siemplify,
                    param_name="additional_data",
                    default_value="{}",
                    input_type=str,
                )
            )
            output_message, result_value, status = query_operation_status(
                siemplify=siemplify,
                manager=manager,
                action_start_time=action_start_time,
                result_data=json.loads(result_data),
            )

    except Exception as err:
        output_message = (
            f"Error executing action {UNISOLATE_ENDPOINT_SCRIPT_NAME}. Reason: {err}"
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
