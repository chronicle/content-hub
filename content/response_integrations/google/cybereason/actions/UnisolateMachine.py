from __future__ import annotations
import json
import sys
from ..core.CybereasonManager import CybereasonManager
from soar_sdk.ScriptResult import (
    EXECUTION_STATE_COMPLETED,
    EXECUTION_STATE_FAILED,
    EXECUTION_STATE_INPROGRESS,
)
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyUtils import output_handler, unix_now
from TIPCommon import extract_configuration_param, extract_action_param
from ..core.constants import (
    INTEGRATION_NAME,
    UNISOLATE_MACHINE_SCRIPT_NAME,
    DEFAULT_TIMEOUT,
    HOSTNAME_SENSOR_KEY,
)
from ..core.exceptions import CybereasonManagerNotFoundError
from ..core.utils import (
    get_entity_original_identifier,
    is_approaching_timeout,
    is_async_action_global_timeout_approaching,
)


def start_operation(siemplify, manager, suitable_entities):
    successful_entities, failed_entities = [], []
    result_value = {
        "for_unisolate": {},
        "already_unisolated": {},
        "completed": {},
        "failed": [],
        "not_found": [],
    }
    status = EXECUTION_STATE_INPROGRESS

    for entity in suitable_entities:
        entity_identifier = get_entity_original_identifier(entity)
        siemplify.LOGGER.info(f"Started processing entity: {entity_identifier}")

        try:
            machine = manager.get_sensor_details(entity_identifier, HOSTNAME_SENSOR_KEY)

            if machine is not None:
                if not machine.isolated:
                    siemplify.LOGGER.info(
                        f"The following machine already unisolated: {entity_identifier}"
                    )
                    result_value["completed"][entity_identifier] = machine.pylum_id
                    successful_entities.append(entity_identifier)
                    continue

                manager.unisolate_machine(machine_pylum_id=machine.pylum_id)
                result_value["for_unisolate"][entity_identifier] = machine.pylum_id
                successful_entities.append(entity_identifier)
            else:
                failed_entities.append(entity_identifier)
                result_value["failed"].append(entity_identifier)
                siemplify.LOGGER.error(
                    f"An error occurred on entity {entity_identifier}"
                )

        except CybereasonManagerNotFoundError as err:
            failed_entities.append(entity_identifier)
            result_value["not_found"].append(entity_identifier)
            siemplify.LOGGER.exception(err)
            siemplify.LOGGER.error(
                f"Machine with {entity_identifier} value not found in {INTEGRATION_NAME}"
            )
        except Exception as err:
            failed_entities.append(entity_identifier)
            result_value["failed"].append(entity_identifier)
            siemplify.LOGGER.error(f"An error occurred on entity {entity_identifier}")
            siemplify.LOGGER.exception(err)

    if successful_entities:
        result_value = json.dumps(result_value)
        output_message = f"Successfully found machines in {INTEGRATION_NAME}: {', '.join(successful_entities)}."
    else:
        output_message = f"None of the machines were found in {INTEGRATION_NAME}."
        result_value = False
        status = EXECUTION_STATE_COMPLETED

    return output_message, result_value, status


def query_operation_status(
    siemplify, manager, action_start_time, result_data, suitable_entities
):
    completed_machines = {}
    timeout_approaching = False
    items_to_unisolate_count = len(result_data["for_unisolate"].keys())

    for entity_identifier, machine_pylum_id in result_data["for_unisolate"].items():
        if is_async_action_global_timeout_approaching(siemplify, action_start_time):
            siemplify.LOGGER.info("Timeout is approaching. Action will gracefully exit")
            timeout_approaching = True
            break
        if is_approaching_timeout(action_start_time, DEFAULT_TIMEOUT):
            siemplify.LOGGER.info(
                f"Action processed {len(completed_machines.keys())} out of {items_to_unisolate_count}"
            )
            break

        siemplify.LOGGER.info(f"Unisolating machine for {entity_identifier} entity.")
        try:
            machine = manager.get_sensor_details(entity_identifier, HOSTNAME_SENSOR_KEY)

            if machine.isolated:
                continue

            siemplify.LOGGER.info(
                f"Machine with {machine_pylum_id} pylum id unisolated: {entity_identifier}"
            )
            completed_machines[entity_identifier] = machine_pylum_id

        except CybereasonManagerNotFoundError as err:
            result_data["not_found"].append(entity_identifier)
            siemplify.LOGGER.exception(err)
            siemplify.LOGGER.error(
                f"Machine with {entity_identifier} value not found in {INTEGRATION_NAME}"
            )
        except Exception as err:
            result_data["failed"].append(entity_identifier)
            siemplify.LOGGER.error(f"An error occurred on entity {entity_identifier}")
            siemplify.LOGGER.exception(err)

    for key in completed_machines.keys():
        result_data["for_unisolate"].pop(key)
    # Update completed entities with completed_entities dict including json_result
    result_data["completed"].update(completed_machines)

    if result_data["for_unisolate"] and not timeout_approaching:
        status = EXECUTION_STATE_INPROGRESS
        result_value = json.dumps(result_data)
        output_message = (
            f"Waiting for unisolation to finish on the following entities: "
            f"{', '.join(result_data['for_unisolate'].keys())}"
        )
    else:
        output_message, result_value, status = finish_operation(
            suitable_entities=suitable_entities,
            result_data=result_data,
            timeout_approaching=timeout_approaching,
        )

    return output_message, result_value, status


def finish_operation(suitable_entities, result_data, timeout_approaching):
    result_value = True
    status = EXECUTION_STATE_COMPLETED
    failed_entities = result_data["failed"]
    not_found_entities = result_data["not_found"]
    successful_entities = []
    not_finished = []
    output_message = ""

    for entity in suitable_entities:
        entity_identifier = get_entity_original_identifier(entity)
        if entity_identifier in result_data["completed"].keys():
            successful_entities.append(entity_identifier)
        if entity_identifier in result_data["for_unisolate"].keys():
            not_finished.append(entity_identifier)

    if successful_entities:
        output_message += (
            f"Successfully unisolated the following machines in {INTEGRATION_NAME}: "
            f"{', '.join(successful_entities)}. \n"
        )

    if failed_entities:
        output_message += (
            f"Action wasn't able to unisolate the following machines in {INTEGRATION_NAME}: "
            f"{', '.join(failed_entities)} \n"
        )
    if not_found_entities:
        output_message += (
            f"The following machines were not found in {INTEGRATION_NAME}: "
            f"{', '.join(not_found_entities)} \n"
        )
    if timeout_approaching and not_finished:
        output_message += (
            f"Unisolate was initiated on the following entities, but wasn't finished: "
            f"{', '.join(not_finished)}. Please execute the action again with bigger timeout. \n"
        )
        status = EXECUTION_STATE_FAILED
        result_value = False
    if not output_message:
        output_message += f"None of the machines were found in {INTEGRATION_NAME}."
        result_value = False

    return output_message, result_value, status


@output_handler
def main(is_first_run):
    siemplify = SiemplifyAction()
    siemplify.script_name = UNISOLATE_MACHINE_SCRIPT_NAME
    action_start_time = unix_now()
    mode = "Main" if is_first_run else "Get Report"
    siemplify.LOGGER.info(f"----------------- {mode} - Param Init -----------------")

    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Root",
        is_mandatory=True,
    )
    username = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Username",
        is_mandatory=True,
    )
    password = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Password",
        is_mandatory=True,
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        default_value=False,
        input_type=bool,
    )
    ca_certificate = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="CA Certificate Base64",
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    output_message = ""
    status = EXECUTION_STATE_INPROGRESS
    result_value = False
    suitable_entities = [
        entity
        for entity in siemplify.target_entities
        if entity.entity_type == EntityTypes.HOSTNAME
    ]

    try:
        manager = CybereasonManager(
            api_root=api_root,
            username=username,
            password=password,
            verify_ssl=verify_ssl,
            ca_certificate_b64=ca_certificate,
            logger=siemplify.LOGGER,
            force_check_connectivity=True,
        )

        if is_first_run:
            output_message, result_value, status = start_operation(
                siemplify, manager=manager, suitable_entities=suitable_entities
            )
        if status == EXECUTION_STATE_INPROGRESS:
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
            )

    except Exception as err:
        output_message = (
            f"Error executing action {UNISOLATE_MACHINE_SCRIPT_NAME}. Reason: {err}"
        )
        result_value = False
        status = EXECUTION_STATE_FAILED
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(err)

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  is_success: {result_value}\n  output_message: {output_message}"
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    is_first_run = len(sys.argv) < 3 or sys.argv[2] == "True"
    main(is_first_run)
