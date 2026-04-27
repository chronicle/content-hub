from __future__ import annotations
import json
import sys
from ..core.IvantiEndpointManagerManager import IvantiEndpointManagerManager
from soar_sdk.ScriptResult import (
    EXECUTION_STATE_COMPLETED,
    EXECUTION_STATE_FAILED,
    EXECUTION_STATE_INPROGRESS,
)
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyUtils import output_handler, unix_now, convert_dict_to_json_result_dict
from TIPCommon import extract_configuration_param, extract_action_param
from ..core.constants import (
    INTEGRATION_NAME,
    INTEGRATION_DISPLAY_NAME,
    SCAN_ENDPOINTS_SCRIPT_NAME,
    DEFAULT_SCAN_NAME,
    DONE_STATUS,
    FAILED_STATUS,
    DEFAULT_TIMEOUT,
)
from ..core.UtilsManager import (
    get_entity_original_identifier,
    is_approaching_timeout,
    is_async_action_global_timeout_approaching,
)


# Fix misalignment of MAC entity type
EntityTypes.MACADDRESS = EntityTypes.MACADDRESS.upper()
SUPPORTED_ENTITY_TYPES = [
    EntityTypes.ADDRESS,
    EntityTypes.HOSTNAME,
    EntityTypes.MACADDRESS,
]


def start_operation(siemplify, manager, suitable_entities, scan_name, only_initiate):
    status = EXECUTION_STATE_INPROGRESS
    result_value = {
        "task_id": "",
        "scan_name": scan_name,
        "json_results": {},
        "machines_guids": {},
        "completed": [],
        "failed": [],
        "not_found": [],
    }

    if suitable_entities:
        machines = manager.get_machines(entities=suitable_entities)

        if machines:
            for entity in suitable_entities:
                entity_details = next(
                    (
                        machine
                        for machine in machines
                        if entity.identifier
                        in [
                            machine.device_name,
                            machine.ip_address,
                            machine.mac_address,
                        ]
                    ),
                    None,
                )
                if entity_details:
                    result_value["machines_guids"][
                        entity.identifier
                    ] = entity_details.guid
                else:
                    result_value["not_found"].append(entity.identifier)

    if result_value["machines_guids"]:
        task_id = manager.create_scan(
            scan_name=scan_name, guids=list(result_value["machines_guids"].values())
        )

        manager.start_task(task_id=task_id)
        result_value["task_id"] = task_id

        if not only_initiate:
            task_result = manager.get_task_result(task_id=task_id)

            for task_machine in task_result.machine_data:
                for key, value in result_value["machines_guids"].items():
                    if value == task_machine.guid:
                        result_value["json_results"][key] = {
                            "status": task_machine.status
                        }
                        if task_machine.status in [DONE_STATUS, FAILED_STATUS]:
                            (
                                result_value["completed"].append(key)
                                if task_machine.status == DONE_STATUS
                                else result_value["failed"].append(key)
                            )
                            result_value["machines_guids"][key] = None

            if result_value["machines_guids"].values():
                output_message = (
                    f"Waiting for scan to finish on the following entities: "
                    f"{', '.join([key for key, value in result_value['machines_guids'].items() if value])}"
                )
                result_value = json.dumps(result_value)
                return output_message, result_value, status

    output_message, result_value, status = finish_operation(
        siemplify=siemplify,
        result_data=result_value,
        timeout_approaching=False,
        suitable_entities=suitable_entities,
    )

    return output_message, result_value, status


def query_operation_status(
    siemplify, manager, action_start_time, result_data, suitable_entities
):
    timeout_approaching = False

    task_id = result_data["task_id"]
    task_result = manager.get_task_result(task_id=task_id)

    if is_async_action_global_timeout_approaching(
        siemplify, action_start_time
    ) or is_approaching_timeout(action_start_time, DEFAULT_TIMEOUT):
        siemplify.LOGGER.info("Timeout is approaching. Action will gracefully exit")
        timeout_approaching = True
    else:
        for task_machine in task_result.machine_data:
            for key, value in result_data["machines_guids"].items():
                if value == task_machine.guid:
                    result_data["json_results"][key] = {"status": task_machine.status}
                    if task_machine.status in [DONE_STATUS, FAILED_STATUS]:
                        (
                            result_data["completed"].append(key)
                            if task_machine.status == DONE_STATUS
                            else result_data["failed"].append(key)
                        )
                        result_data["machines_guids"][key] = None

        if result_data["machines_guids"].values():
            output_message = (
                f"Waiting for scan to finish on the following entities: "
                f"{', '.join([key for key, value in result_data['machines_guids'].items() if value])}"
            )
            result_value = json.dumps(result_data)
            return output_message, result_value, EXECUTION_STATE_INPROGRESS

    output_message, result_value, status = finish_operation(
        siemplify=siemplify,
        result_data=result_data,
        timeout_approaching=timeout_approaching,
        suitable_entities=suitable_entities,
    )

    return output_message, result_value, status


def finish_operation(siemplify, result_data, timeout_approaching, suitable_entities):
    result_value = True
    status = EXECUTION_STATE_COMPLETED
    output_message = ""
    successful_entities = []
    failed_entities = []
    not_found_entities = []
    initiated_entities = []
    json_results = result_data.get("json_results", {})

    for entity in suitable_entities:
        entity_identifier = get_entity_original_identifier(entity)
        if entity_identifier in result_data["completed"]:
            successful_entities.append(entity_identifier)
        elif entity_identifier in result_data["failed"]:
            failed_entities.append(entity_identifier)
        elif entity_identifier in result_data["not_found"]:
            not_found_entities.append(entity_identifier)
        elif entity_identifier in list(result_data["machines_guids"].keys()):
            initiated_entities.append(entity_identifier)

    if json_results:
        siemplify.result.add_result_json(convert_dict_to_json_result_dict(json_results))
        if successful_entities:
            output_message += (
                f"Successfully executed vulnerability scan on the following entities in "
                f"{INTEGRATION_DISPLAY_NAME}: "
                f"{', '.join([entity for entity in successful_entities])}\n"
            )

        if failed_entities:
            output_message += (
                f"Action wasn't able to execute vulnerability scan on the following entities in "
                f"{INTEGRATION_DISPLAY_NAME}: "
                f"{', '.join([entity for entity in failed_entities])}\n"
            )

        if not successful_entities:
            result_value = False
            output_message = (
                f"Action wasn't able to execute vulnerability scan on the provided entities in "
                f"{INTEGRATION_DISPLAY_NAME}.\n"
            )

    if not_found_entities:
        output_message += (
            f"The following entities were not found in {INTEGRATION_DISPLAY_NAME}: "
            f"{', '.join([entity for entity in not_found_entities])}\n"
        )

    if not successful_entities and not failed_entities:
        if initiated_entities:
            result_value = True
            siemplify.result.add_result_json({"task_id": result_data["task_id"]})
            output_message = (
                f"Successfully initiated vulnerability scan on the following entities in "
                f"{INTEGRATION_DISPLAY_NAME}: "
                f"{', '.join([entity for entity in initiated_entities])}\n"
            )
        else:
            result_value = False
            output_message = f"None of the provided entities were found in {INTEGRATION_DISPLAY_NAME}."

    if timeout_approaching and initiated_entities:
        raise Exception(
            f"action ran into a timeout during execution. "
            f"Pending entities: {', '.join([entity for entity in initiated_entities])}\n"
            f'Please increase the timeout in IDE or enable "Only Initiate".'
        )

    return output_message, result_value, status


@output_handler
def main(is_first_run):
    siemplify = SiemplifyAction()
    action_start_time = unix_now()
    siemplify.script_name = SCAN_ENDPOINTS_SCRIPT_NAME
    mode = "Main" if is_first_run else "Scan Endpoints"
    siemplify.LOGGER.info(f"----------------- {mode} - Param Init -----------------")

    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Root",
        is_mandatory=True,
        print_value=True,
    )
    username = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Username",
        is_mandatory=True,
        print_value=True,
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
        is_mandatory=True,
        input_type=bool,
        print_value=True,
    )

    # Action parameters
    task_name = extract_action_param(
        siemplify,
        param_name="Task Name",
        default_value=DEFAULT_SCAN_NAME,
        print_value=True,
    )
    only_initiate = extract_action_param(
        siemplify, param_name="Only Initiate", input_type=bool, print_value=True
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
        manager = IvantiEndpointManagerManager(
            api_root=api_root,
            username=username,
            password=password,
            verify_ssl=verify_ssl,
            siemplify_logger=siemplify.LOGGER,
        )

        if is_first_run:
            output_message, result_value, status = start_operation(
                siemplify,
                manager=manager,
                suitable_entities=suitable_entities,
                scan_name=task_name,
                only_initiate=only_initiate,
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
            f"Error executing action {SCAN_ENDPOINTS_SCRIPT_NAME}. Reason: {err}"
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
