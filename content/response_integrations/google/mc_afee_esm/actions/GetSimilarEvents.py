from __future__ import annotations
import sys
import json
import copy

from typing import Tuple, List, Dict, Any

from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyUtils import output_handler, unix_now, convert_dict_to_json_result_dict
from soar_sdk.ScriptResult import (
    EXECUTION_STATE_COMPLETED,
    EXECUTION_STATE_INPROGRESS,
    EXECUTION_STATE_FAILED,
)
from ..core.McAfeeESMManager import McAfeeESMManager
from ..core.McAfeeESMExceptions import BadRequestException
from TIPCommon import (
    construct_csv,
    extract_configuration_param,
    extract_action_param,
    is_approaching_timeout,
)
from ..core.constants import (
    INTEGRATION_NAME,
    GET_SIMILAR_EVENTS_SCRIPT_NAME,
    DEFAULT_LIMIT,
    DEFAULT_HOURS_BACK,
    GLOBAL_TIMEOUT_THRESHOLD_IN_MIN,
    DEFAULT_TIMEOUT,
    SEARCH_BY_ADDRESS_QUERY_COMPONENT,
    SEARCH_BY_USER_QUERY_COMPONENT,
    SEARCH_BY_HOST_QUERY_COMPONENT,
)

SUPPORTED_ENTITY_TYPES = [EntityTypes.ADDRESS, EntityTypes.HOSTNAME, EntityTypes.USER]


def start_operation(
    siemplify: SiemplifyAction,
    manager: McAfeeESMManager,
    action_start_time: int,
    hours_back: int,
    ips_id: str,
    limit: int,
    suitable_entities: List,
) -> Tuple[str, bool, int]:
    result_data = {
        "result_urls": {},
        "json_results": {},
        "table_results": {},
        "completed": [],
        "failed": [],
    }

    for entity in suitable_entities:
        siemplify.LOGGER.info(f"Started processing entity: {entity.identifier}")
        try:
            if entity.entity_type == EntityTypes.ADDRESS:
                search_component = copy.deepcopy(SEARCH_BY_ADDRESS_QUERY_COMPONENT)
            elif entity.entity_type == EntityTypes.HOSTNAME:
                search_component = copy.deepcopy(SEARCH_BY_HOST_QUERY_COMPONENT)
            else:
                search_component = copy.deepcopy(SEARCH_BY_USER_QUERY_COMPONENT)

            query = manager.build_events_query(
                search_component=search_component,
                entity_identifier=entity.identifier,
                ips_id=ips_id,
                hours_back=hours_back,
                results_limit=limit,
            )

            result_url = manager.run_events_query(query=query)
            result_data["result_urls"][entity.identifier] = result_url
        except BadRequestException as e:
            result_data["failed"].append(entity.identifier)
            siemplify.LOGGER.error(f"An error occurred on entity {entity.identifier}")
            siemplify.LOGGER.exception(e)
        siemplify.LOGGER.info(f"Finished processing entity: {entity.identifier}")

    output_message, result_value, status = query_operation_status(
        siemplify, manager, result_data, action_start_time, limit
    )

    return output_message, result_value, status


def query_operation_status(
    siemplify: SiemplifyAction,
    manager: McAfeeESMManager,
    result_data: Dict,
    action_start_time: int,
    limit: int,
) -> Tuple[str, Any, int]:

    result_urls = result_data["result_urls"]
    for entity_identifier, result_url in result_urls.items():
        ready_results_url = None
        try:
            ready_results_url = manager.check_events_query_status(location=result_url)
        except BadRequestException as e:
            result_data["failed"].append(entity_identifier)
            result_data["result_urls"][entity_identifier] = None
            siemplify.LOGGER.error(f"An error occurred on entity {entity_identifier}")
            siemplify.LOGGER.exception(e)

        if (
            siemplify.execution_deadline_unix_time_ms - action_start_time
            < GLOBAL_TIMEOUT_THRESHOLD_IN_MIN * 60
            or is_approaching_timeout(action_start_time, DEFAULT_TIMEOUT)
        ):
            raise Exception(
                "action initiated the query but ran into a timeout during data "
                "retrieval. Please increase the timeout in the IDE and try again."
            )
        else:
            if ready_results_url:
                query_result = manager.get_events_query_results(
                    location=ready_results_url, limit=limit
                )
                result_data["result_urls"][entity_identifier] = None
                if query_result.data:
                    result_data["json_results"][
                        entity_identifier
                    ] = query_result.to_json_list()
                    result_data["table_results"][entity_identifier] = construct_csv(
                        query_result.to_json_list()
                    )
                    result_data["completed"].append(entity_identifier)
                else:
                    result_data["failed"].append(entity_identifier)

    result_data["result_urls"] = {
        k: v for k, v in result_data["result_urls"].items() if v
    }
    if any(result_data["result_urls"].values()):
        output_message = f"Waiting for the query to finish for: {', '.join( [ key for key, value in result_data['result_urls'].items() if value ] )}"
        result_value = json.dumps(result_data)
        return output_message, result_value, EXECUTION_STATE_INPROGRESS

    status = EXECUTION_STATE_COMPLETED
    result_value = True
    output_message = ""

    if result_data["completed"]:
        siemplify.result.add_result_json(
            convert_dict_to_json_result_dict(result_data["json_results"])
        )
        for identifier, table_data in result_data["table_results"].items():
            siemplify.result.add_entity_table(identifier, table_data)
        output_message = (
            "Successfully retrieved events for the following entities in {}: "
            "{}\n".format(
                INTEGRATION_NAME,
                ", ".join([entity for entity in result_data["completed"]]),
            )
        )

    if result_data["failed"]:
        output_message += (
            "\nAction wasn't able to retrieve events for the following entities in {}: "
            "{}.\n".format(
                INTEGRATION_NAME,
                ", ".join([entity for entity in result_data["failed"]]),
            )
        )

    if not result_data["completed"]:
        output_message = (
            f"No events were found for the provided entities in {INTEGRATION_NAME}"
        )
        result_value = False

    return output_message, result_value, status


@output_handler
def main(is_first_run):
    siemplify = SiemplifyAction()
    action_start_time = unix_now()
    siemplify.script_name = GET_SIMILAR_EVENTS_SCRIPT_NAME

    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    api_root = extract_configuration_param(
        siemplify=siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Root",
        is_mandatory=True,
        print_value=True,
    )
    username = extract_configuration_param(
        siemplify=siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Username",
        is_mandatory=True,
        print_value=True,
    )
    password = extract_configuration_param(
        siemplify=siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Password",
        remove_whitespaces=False,
        is_mandatory=True,
    )
    product_version = extract_configuration_param(
        siemplify=siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Product Version",
        is_mandatory=True,
        print_value=True,
    )
    use_aes_encryption = extract_configuration_param(
        siemplify=siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Use AES Encryption",
        input_type=bool,
        print_value=True,
    )
    verify_ssl = extract_configuration_param(
        siemplify=siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        is_mandatory=True,
        input_type=bool,
        print_value=True,
    )

    hours_back = extract_action_param(
        siemplify,
        param_name="Hours Back",
        print_value=True,
        input_type=int,
        is_mandatory=True,
        default_value=DEFAULT_HOURS_BACK,
    )
    ips_id = extract_action_param(
        siemplify, param_name="IPS ID", print_value=True, is_mandatory=False
    )
    limit = extract_action_param(
        siemplify,
        param_name="Result Limit",
        print_value=True,
        input_type=int,
        is_mandatory=False,
        default_value=DEFAULT_LIMIT,
    )

    result_value = False
    status = EXECUTION_STATE_COMPLETED
    suitable_entities = [
        entity
        for entity in siemplify.target_entities
        if entity.entity_type in SUPPORTED_ENTITY_TYPES
    ]
    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    try:
        if limit < 1 or limit > 200:
            raise Exception(
                f'Invalid value provided for "Result Limit": {limit}. '
                f"Should be in range from 1 to 200."
            )

        if hours_back < 1:
            raise Exception(
                f'Invalid value provided for "Hours Back": {hours_back}. '
                f"Positive number should be provided."
            )

        if not suitable_entities:
            output_message = "No suitable entities found in the scope"
        else:
            manager = McAfeeESMManager(
                api_root=api_root,
                username=username,
                password=password,
                product_version=product_version,
                verify_ssl=verify_ssl,
                siemplify_logger=siemplify.LOGGER,
                siemplify_scope=siemplify,
                use_aes_encryption=use_aes_encryption,
            )

            if is_first_run:
                output_message, result_value, status = start_operation(
                    siemplify,
                    manager=manager,
                    action_start_time=action_start_time,
                    hours_back=hours_back,
                    ips_id=ips_id,
                    limit=limit,
                    suitable_entities=suitable_entities,
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
                    limit=limit,
                )
    except Exception as e:
        output_message = (
            f"Error executing action {GET_SIMILAR_EVENTS_SCRIPT_NAME}. Reason: {e}"
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
