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
from ..core.McAfeeESMManager import McAfeeESMManager
from ..core.McAfeeESMExceptions import BadRequestException
from ..core.utils import get_timestamps
from TIPCommon import (
    construct_csv,
    extract_configuration_param,
    extract_action_param,
    convert_comma_separated_to_list,
    is_approaching_timeout,
)
from ..core.constants import (
    INTEGRATION_NAME,
    SEND_ENTITY_QUERY_SCRIPT_NAME,
    DEFAULT_LIMIT,
    CUSTOM_TIME_FILTER,
    DEFAULT_QUERY_FIELDS,
    GLOBAL_TIMEOUT_THRESHOLD_IN_MIN,
    DEFAULT_TIMEOUT,
    SORT_ORDER,
    EVENT_QUERY_TYPE,
    DOT_STRING,
)

QUERY_RESULTS_TABLE_NAME = "Query Results"
SUPPORTED_ENTITY_TYPES = [EntityTypes.ADDRESS, EntityTypes.HOSTNAME]


def start_operation(
    siemplify: SiemplifyAction,
    manager: McAfeeESMManager,
    action_start_time: int,
    time_range: str,
    start_time: str,
    end_time: str,
    filter_field_name: str,
    filter_operator: str,
    filter_values: List,
    fields_to_fetch: List,
    sort_field: str,
    sort_order: str,
    query_type: str,
    limit: int,
    suitable_entities: List,
    ip_entity_key: str,
    hostname_entity_key: str,
) -> Tuple[str, bool, int]:
    result_data = {
        "result_ids": {},
        "json_results": {},
        "table_results": {},
        "completed": [],
        "failed": [],
        "not_found": [],
    }
    first_error_msg = ""
    for entity in suitable_entities:
        siemplify.LOGGER.info(f"Started processing entity: {entity.identifier}")
        try:
            entity_key = (
                ip_entity_key
                if entity.entity_type == EntityTypes.ADDRESS
                else hostname_entity_key
            )
            query = manager.build_query(
                fields_to_return=fields_to_fetch,
                time_filter=time_range,
                start_time=start_time,
                end_time=end_time,
                filter_field_name=filter_field_name,
                filter_operator=filter_operator,
                filter_values=filter_values,
                sort_field=sort_field,
                sort_order=sort_order,
                limit=limit,
                entity_identifier=entity.identifier,
                entity_key=entity_key,
            )

            result_id = manager.execute_query(query_type=query_type, query=query)
            result_data["result_ids"][entity.identifier] = result_id
        except BadRequestException as e:
            if not first_error_msg:
                first_error_msg = e
            result_data["failed"].append(entity.identifier)
            siemplify.LOGGER.error(f"An error occurred on entity {entity.identifier}")
            siemplify.LOGGER.exception(e)
        siemplify.LOGGER.info(f"Finished processing entity: {entity.identifier}")

    if not result_data["result_ids"]:
        raise Exception(first_error_msg)

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

    result_ids = result_data["result_ids"]
    first_error_msg = ""
    for entity_identifier, result_id in result_ids.items():
        is_query_ready = False
        try:
            query_result = manager.check_query_status(result_id=result_id)
            is_query_ready = query_result.complete
        except BadRequestException as e:
            if not first_error_msg:
                first_error_msg = e
            result_data["failed"].append(entity_identifier)
            result_data["result_ids"][entity_identifier] = None
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
            if is_query_ready:
                siemplify.LOGGER.info(
                    f"Query results for Query ID {result_id} are ready."
                )
                query_result = manager.get_query_results(
                    result_id=result_id, limit=limit
                )
                result_data["result_ids"][entity_identifier] = None
                if query_result.rows:
                    result_data["json_results"][
                        entity_identifier
                    ] = query_result.to_json_list()
                    result_data["table_results"][entity_identifier] = construct_csv(
                        query_result.to_json_list()
                    )
                    result_data["completed"].append(entity_identifier)
                else:
                    result_data["not_found"].append(entity_identifier)

    if not result_data["completed"] and not result_data["not_found"]:
        raise Exception(first_error_msg)

    result_data["result_ids"] = {
        k: v for k, v in result_data["result_ids"].items() if v
    }
    if any(result_data["result_ids"].values()):
        output_message = f"Waiting for results for the following entities: {', '.join( [ key for key, value in result_data['result_ids'].items() if value ] )}"
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
            "Successfully retrieved data for the provided query in {} for the following entities in: "
            "{}\n".format(
                INTEGRATION_NAME,
                ", ".join([entity for entity in result_data["completed"]]),
            )
        )

    if result_data["failed"]:
        output_message += (
            "\nQueries were not executed in McAfee ESM for the following entities: "
            "{}.\nPlease check the configuration.\n"
            "".format(", ".join([entity for entity in result_data["failed"]]))
        )

    if result_data["not_found"]:
        output_message += (
            "\nNo data was found in {} for the following entities: "
            "{}\n".format(
                INTEGRATION_NAME,
                ", ".join([entity for entity in result_data["not_found"]]),
            )
        )

    if not result_data["completed"]:
        if not result_data["failed"]:
            output_message = (
                f"No data was found for the provided entities in {INTEGRATION_NAME}"
            )

        if not result_data["not_found"]:
            output_message = (
                "Action wasn't able to create a query for the provided entities. "
                "Make sure to check that the fields/values are provided correctly."
            )

        result_value = False

    return output_message, result_value, status


@output_handler
def main(is_first_run):
    siemplify = SiemplifyAction()
    action_start_time = unix_now()
    siemplify.script_name = SEND_ENTITY_QUERY_SCRIPT_NAME

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

    ip_entity_key = extract_action_param(
        siemplify,
        param_name="IP Address Entity Key",
        print_value=True,
        is_mandatory=True,
    )
    hostname_entity_key = extract_action_param(
        siemplify, param_name="Hostname Entity Key", print_value=True, is_mandatory=True
    )
    time_range = extract_action_param(
        siemplify, param_name="Time Range", print_value=True, is_mandatory=True
    )
    start_time = extract_action_param(
        siemplify, param_name="Start Time", print_value=True
    )
    end_time = extract_action_param(siemplify, param_name="End Time", print_value=True)
    filter_field_name = extract_action_param(
        siemplify, param_name="Filter Field Name", print_value=True, is_mandatory=True
    )
    filter_operator = extract_action_param(
        siemplify, param_name="Filter Operator", print_value=True, is_mandatory=True
    )
    filter_values = extract_action_param(
        siemplify, param_name="Filter Values", print_value=True, is_mandatory=True
    )
    fields_to_fetch = extract_action_param(
        siemplify, param_name="Fields To Fetch", print_value=True
    )
    sort_field = extract_action_param(
        siemplify, param_name="Sort Field", print_value=True
    )
    sort_order = extract_action_param(
        siemplify, param_name="Sort Order", print_value=True
    )
    limit = extract_action_param(
        siemplify,
        param_name="Max Results To Return",
        input_type=int,
        default_value=DEFAULT_LIMIT,
        print_value=True,
    )

    query_type = EVENT_QUERY_TYPE
    filter_values = convert_comma_separated_to_list(filter_values)
    if fields_to_fetch:
        fields_to_fetch = convert_comma_separated_to_list(fields_to_fetch)
    else:
        fields_to_fetch = DEFAULT_QUERY_FIELDS.get(query_type)

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
                f'Invalid value was provided for "Max Results to Return": {limit}. '
                f"Should be in range from 1 to 200."
            )

        if time_range == CUSTOM_TIME_FILTER:
            start_time, end_time = get_timestamps(start_time, end_time)

        sort_field = (
            sort_field.split(DOT_STRING)[1]
            if sort_field and DOT_STRING in sort_field
            else ""
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
                    time_range=time_range,
                    start_time=start_time,
                    end_time=end_time,
                    filter_field_name=filter_field_name,
                    filter_operator=filter_operator,
                    filter_values=filter_values,
                    fields_to_fetch=fields_to_fetch,
                    sort_field=sort_field,
                    sort_order=SORT_ORDER.get(sort_order),
                    query_type=query_type,
                    limit=limit,
                    suitable_entities=suitable_entities,
                    ip_entity_key=ip_entity_key,
                    hostname_entity_key=hostname_entity_key,
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
            f"Error executing action {SEND_ENTITY_QUERY_SCRIPT_NAME}. Reason: {e}"
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
