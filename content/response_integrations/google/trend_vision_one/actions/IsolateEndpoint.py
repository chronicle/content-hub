from __future__ import annotations
import sys
import json
from typing import Tuple, List, Dict, Any
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyUtils import output_handler, unix_now, convert_dict_to_json_result_dict
from soar_sdk.ScriptResult import (
    EXECUTION_STATE_COMPLETED,
    EXECUTION_STATE_INPROGRESS,
    EXECUTION_STATE_FAILED,
)
from TIPCommon import (
    extract_configuration_param,
    extract_action_param,
    is_approaching_timeout,
    string_to_multi_value,
)
from ..core.constants import (
    INTEGRATION_NAME,
    INTEGRATION_DISPLAY_NAME,
    ISOLATE_ENDPOINT_SCRIPT_NAME,
    SUCCESS_STATUS,
    FAILED_STATUS,
    REJECTED_STATUS,
    RUNNING_STATUS,
    GLOBAL_TIMEOUT_THRESHOLD_IN_MIN,
    DEFAULT_TIMEOUT,
)
from ..core.datamodels import AgentResult
from ..core.TrendVisionOneExceptions import (
    TrendVisionOneException,
    TrendVisionOneTimeoutException,
)
from ..core.TrendVisionOneManager import TrendVisionOneManager
from ..core.UtilsManager import get_entity_original_identifier, process_agents


SUPPORTED_ENTITY_TYPES = [EntityTypes.ADDRESS, EntityTypes.HOSTNAME]


def isolate_agents(
    manager: TrendVisionOneManager,
    agent_uuids: list[str],
    description: str,
    result_data: dict[str, Any],
) -> None:
    """Run a custom script on a list of agents.

    Args:
        manager (TrendVisionOneManager): An instance of the TrendVisionOneManager for
        interacting with the API.
        agent_uuids (list[str]): A list of agent UUIDs to run the script on.
        description (str): Description of isolation.
        result_data (dict[str, Any]): A dictionary to store the results of the
        operation.
        logger (SiemplifyLogger): The Siemplify logger for logging information and
        errors.
    """
    agents: AgentResult = process_agents(
        manager=manager,
        agent_uids=agent_uuids,
    )
    result_data["failed"].extend(agents.failed_agents)
    for endpoint in agents.successful_agents:
        if endpoint.guid in result_data["result_endpoints"]:
            result_data["result_urls"][endpoint.guid] = result_data[
                "result_endpoints"
            ][endpoint.guid]

        else:
            try:
                result_url = manager.isolate_endpoint(
                    description=description,
                    guid=endpoint.guid
                )

            except TrendVisionOneException as e:
                if endpoint.guid not in result_data["failed"]:
                    result_data["failed"].append(endpoint.guid)
                manager.siemplify.LOGGER.error(
                    f"Isolation failed no agent {endpoint.guid}"
                )
                manager.siemplify.LOGGER.exception(e)
                continue
            result_data["result_urls"][endpoint.guid] = result_url
            result_data["result_endpoints"][endpoint.guid] = result_url


def start_operation(
    siemplify: SiemplifyAction,
    manager: TrendVisionOneManager,
    action_start_time: int,
    description: str,
    suitable_entities: List,
    agent_uuids: list[str],
) -> Tuple[str, bool, int]:
    result_data = {
        "result_urls": {},
        "result_endpoints": {},
        "json_results": {},
        "completed": [],
        "failed": [],
    }
    for entity in suitable_entities:
        siemplify.LOGGER.info(f"Started processing entity: {entity.identifier}")
        entity_identifier = get_entity_original_identifier(entity)
        try:
            if entity.entity_type == EntityTypes.ADDRESS:
                endpoint = manager.search_endpoint(ip=entity_identifier)
            else:
                endpoint = manager.search_endpoint(hostname=entity_identifier)

            if endpoint:
                if endpoint.guid in result_data["result_endpoints"]:
                    result_data["result_urls"][entity.identifier] = result_data[
                        "result_endpoints"
                    ][endpoint.guid]
                else:
                    result_url = manager.isolate_endpoint(
                        description=description, guid=endpoint.guid
                    )
                    result_data["result_urls"][entity.identifier] = result_url
                    result_data["result_endpoints"][endpoint.guid] = result_url
            else:
                result_data["failed"].append(entity.identifier)
                siemplify.LOGGER.info(
                    f"No endpoint found for the entity: {entity.identifier}"
                )
        except Exception as e:
            result_data["failed"].append(entity.identifier)
            siemplify.LOGGER.error(f"An error occurred on entity {entity.identifier}")
            siemplify.LOGGER.exception(e)
        siemplify.LOGGER.info(f"Finished processing entity: {entity.identifier}")

    isolate_agents(
        manager=manager,
        agent_uuids=agent_uuids,
        description=description,
        result_data=result_data,
    )
    output_message, result_value, status = query_operation_status(
        siemplify, manager, result_data, action_start_time
    )
    return output_message, result_value, status


def query_operation_status(
    siemplify: SiemplifyAction,
    manager: TrendVisionOneManager,
    result_data: Dict,
    action_start_time: int,
) -> Tuple[str, Any, int]:
    results_urls = result_data["result_urls"]
    for entity_identifier, result_url in results_urls.items():
        task_details = manager.get_task(task_url=result_url)
        if (
            siemplify.execution_deadline_unix_time_ms - action_start_time
            < GLOBAL_TIMEOUT_THRESHOLD_IN_MIN * 60 * 1000
            or is_approaching_timeout(action_start_time, DEFAULT_TIMEOUT)
        ):
            raise TrendVisionOneTimeoutException(
                "action ran into a timeout during execution. "
            )
        else:
            if task_details.status == SUCCESS_STATUS:
                siemplify.LOGGER.info(
                    f"Successfully isolated entity {entity_identifier}"
                )
                result_data["result_urls"][entity_identifier] = None
                result_data["json_results"][entity_identifier] = {
                    "task_id": task_details.id,
                    "status": task_details.status,
                }
                result_data["completed"].append(entity_identifier)
            elif task_details.status == RUNNING_STATUS:
                result_data["json_results"][entity_identifier] = {
                    "task_id": task_details.id,
                    "status": task_details.status,
                }
            elif task_details.status in [FAILED_STATUS, REJECTED_STATUS]:
                result_data["result_urls"][entity_identifier] = None
                result_data["json_results"][entity_identifier] = {
                    "task_id": task_details.id,
                    "status": task_details.status,
                }
                result_data["failed"].append(entity_identifier)

    result_data["result_urls"] = {
        k: v for k, v in result_data["result_urls"].items() if v
    }
    if any(result_data["result_urls"].values()):
        output_message = f"Pending endpoints: {', '.join( [ key for key, value in result_data['result_urls'].items() if value ] )}"
        result_value = json.dumps(result_data)
        return output_message, result_value, EXECUTION_STATE_INPROGRESS

    status = EXECUTION_STATE_COMPLETED

    if result_data["json_results"]:
        siemplify.result.add_result_json(
            convert_dict_to_json_result_dict(result_data["json_results"])
        )

    output_message, result_value = generate_output_message_and_result(result_data)

    return output_message, result_value, status


def generate_output_message_and_result(result_data):
    result_value = True

    if result_data["completed"]:
        output_message = (
            "Successfully isolated the following endpoints {} in: "
            "{}\n".format(
                INTEGRATION_DISPLAY_NAME,
                ", ".join([entity for entity in result_data["completed"]]),
            )
        )
        if result_data["failed"]:
            result_value = False
            output_message += (
                "Action wasn't able to isolate the following endpoints in: "
                "{}: {}\n".format(
                    INTEGRATION_DISPLAY_NAME,
                    ", ".join([entity for entity in result_data["failed"]]),
                )
            )
    else:
        output_message = "None of the provided endpoints were isolated."
        result_value = False

    return output_message, result_value


@output_handler
def main(is_first_run):
    siemplify = SiemplifyAction()
    action_start_time = unix_now()
    siemplify.script_name = ISOLATE_ENDPOINT_SCRIPT_NAME

    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Root",
        is_mandatory=True,
        print_value=True,
    )
    api_token = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Token",
        is_mandatory=True,
        remove_whitespaces=False,
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        is_mandatory=True,
        input_type=bool,
        print_value=True,
    )
    description = extract_action_param(
        siemplify, param_name="Description", print_value=True, is_mandatory=False
    )
    agent_uuids = string_to_multi_value(
        extract_action_param(
            siemplify,
            param_name="Agent UUID",
            print_value=True,
        )
    )

    result_value = False
    result_data = {}
    status = EXECUTION_STATE_COMPLETED
    suitable_entities = [
        entity
        for entity in siemplify.target_entities
        if entity.entity_type in SUPPORTED_ENTITY_TYPES
    ]
    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    try:
        if not suitable_entities:
            output_message = "No suitable entities found in the scope"
        else:
            manager = TrendVisionOneManager(
                api_root=api_root,
                api_token=api_token,
                verify_ssl=verify_ssl,
                siemplify=siemplify,
            )
            manager.test_connectivity()

            if is_first_run:
                output_message, result_value, status = start_operation(
                    siemplify,
                    manager=manager,
                    action_start_time=action_start_time,
                    description=description,
                    suitable_entities=suitable_entities,
                    agent_uuids=agent_uuids,
                )
            else:
                result_data = json.loads(
                    extract_action_param(
                        siemplify, param_name="additional_data", default_value="{}"
                    )
                )
                output_message, result_value, status = query_operation_status(
                    siemplify=siemplify,
                    manager=manager,
                    result_data=result_data,
                    action_start_time=action_start_time,
                )

    except TrendVisionOneTimeoutException as e:
        output_message = (
            f"Error executing action {ISOLATE_ENDPOINT_SCRIPT_NAME}. Reason: {e}\n"
        )
        status = EXECUTION_STATE_FAILED

        if result_data:
            json_results = result_data.get("json_results", {})
            siemplify.result.add_result_json(
                convert_dict_to_json_result_dict(json_results)
            )

            output_message_for_finished, _ = generate_output_message_and_result(
                result_data
            )
            output_message += output_message_for_finished

        output_message += (
            f"Pending endpoints: {', '.join([key for key, value in result_data['result_urls'].items() if value])}. "
            "Please increase the timeout in IDE."
        )

        result_value = False
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)

    except Exception as e:
        output_message = (
            f"Error executing action {ISOLATE_ENDPOINT_SCRIPT_NAME}. Reason: {e}"
        )
        status = EXECUTION_STATE_FAILED
        result_value = False
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  results: {result_value}\n  output_message: {output_message}"
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    is_first_run = len(sys.argv) < 3 or sys.argv[2] == "True"
    main(is_first_run)
