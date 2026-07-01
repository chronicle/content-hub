# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.ScriptResult import (
    EXECUTION_STATE_COMPLETED,
    EXECUTION_STATE_INPROGRESS,
    EXECUTION_STATE_FAILED,
)
from ..core.SplunkManager import SplunkManager
from soar_sdk.SiemplifyDataModel import EntityTypes
from TIPCommon.extraction import extract_configuration_param, extract_action_param
from TIPCommon.transformation import construct_csv
from ..core.constants import (
    DEFAULT_QUERY_LIMIT,
    EMAIL_PATTERN,
    EXECUTE_ENTITY_QUERY_SCRIPT_NAME,
    FROM_TIME_DEFAULT,
    INTEGRATION_NAME,
    QUERY_RESULTS_TABLE_NAME,
    TO_TIME_DEFAULT,
)
import sys
import re
import time
from ..core.UtilsManager import get_entity_original_identifier
from ..core.exceptions import MissingEntityKeysException, AdhocSearchLevelException

SUITABLE_ENTITY_TYPES = [
    EntityTypes.HOSTNAME,
    EntityTypes.USER,
    EntityTypes.FILEHASH,
    EntityTypes.ADDRESS,
    EntityTypes.URL,
]
MAX_ATTEMPT_FOR_JOB_RESULT = 3


def start_operation(
    siemplify,
    manager,
    search_mode,
    query,
    suitable_entities,
    types_mapper,
    result_fields,
    limit,
):
    from_time = extract_action_param(
        siemplify,
        param_name="Results from",
        print_value=True,
        default_value=FROM_TIME_DEFAULT,
    )
    to_time = extract_action_param(
        siemplify,
        param_name="Results To",
        print_value=True,
        default_value=TO_TIME_DEFAULT,
    )
    cross_operator = extract_action_param(
        siemplify,
        param_name="Cross Entity Operator",
        is_mandatory=True,
        print_value=True,
    )

    output_message = f"Successfully started searching: {query}"
    status = EXECUTION_STATE_INPROGRESS

    result_value = manager.search_job_for_query(
        search_mode=search_mode,
        query=query,
        limit=limit,
        from_time=from_time,
        to_time=to_time,
        fields=result_fields,
        separated_entities=suitable_entities,
        operator=cross_operator,
        types_mapper=types_mapper,
    )

    return output_message, result_value, status


def wait_and_check_if_job_id_done(manager, sid):
    for i in range(MAX_ATTEMPT_FOR_JOB_RESULT):
        if manager.is_job_done(sid=sid):
            return True
        time.sleep(3)
    return False


def query_operation_status(siemplify, manager, result, query, result_fields, limit):
    status = EXECUTION_STATE_INPROGRESS
    result_value = result
    sid = result_value
    output_message = f"Waiting for query {query} to finish execution."

    if wait_and_check_if_job_id_done(manager, sid):
        output_message, result_value, status = finish_operation(
            siemplify, manager, sid, query, result_fields, limit
        )

    return output_message, result_value, status


def finish_operation(siemplify, manager, sid, query, result_fields, limit):
    result_value = True
    status = EXECUTION_STATE_COMPLETED

    job_details = manager.get_job_results(sid, limit=limit)
    if job_details:
        result_json = [job_detail.to_json() for job_detail in job_details]
        table_result = [
            job_detail.to_filtered_csv(result_fields) for job_detail in job_details
        ]
        siemplify.result.add_data_table(
            QUERY_RESULTS_TABLE_NAME, construct_csv(table_result)
        )
        siemplify.result.add_result_json(result_json)

        output_message = (
            "Successfully returned results "
            f"for the query '{query}' in {INTEGRATION_NAME}"
        )
    else:
        result_value = False
        output_message = (
            f"No results were found for the query '{query}' in {INTEGRATION_NAME}"
        )

    manager.delete_job(sid=sid)

    return output_message, result_value, status


def validate_entities(
    suitable_entities, ip_key, hostname_key, filehash_key, user_key, url_key, email_key
):
    suitable_entities_by_type = {}
    types_mapper = {}
    if ip_key:
        suitable_entities_by_type["ips"] = [
            get_entity_original_identifier(entity)
            for entity in suitable_entities
            if entity.entity_type == EntityTypes.ADDRESS
        ]
        types_mapper["ips"] = ip_key

    if hostname_key:
        suitable_entities_by_type["hosts"] = [
            get_entity_original_identifier(entity)
            for entity in suitable_entities
            if entity.entity_type == EntityTypes.HOSTNAME
        ]
        types_mapper["hosts"] = hostname_key

    if filehash_key:
        suitable_entities_by_type["filehashes"] = [
            get_entity_original_identifier(entity)
            for entity in suitable_entities
            if entity.entity_type == EntityTypes.FILEHASH
        ]
        types_mapper["filehashes"] = filehash_key

    if user_key:
        suitable_entities_by_type["users"] = [
            get_entity_original_identifier(entity)
            for entity in suitable_entities
            if entity.entity_type == EntityTypes.USER
        ]
        types_mapper["users"] = user_key

    if url_key:
        suitable_entities_by_type["urls"] = [
            get_entity_original_identifier(entity)
            for entity in suitable_entities
            if entity.entity_type == EntityTypes.URL
        ]
        types_mapper["urls"] = url_key

    if email_key:
        suitable_entities_by_type["emails"] = [
            get_entity_original_identifier(entity)
            for entity in suitable_entities
            if (
                entity.entity_type == EntityTypes.USER
                and re.search(EMAIL_PATTERN, get_entity_original_identifier(entity))
            )
        ]
        types_mapper["emails"] = email_key

    return suitable_entities_by_type, types_mapper


@output_handler
def main(is_first_run):
    siemplify = SiemplifyAction()
    siemplify.script_name = EXECUTE_ENTITY_QUERY_SCRIPT_NAME

    url = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Api Root",
        print_value=True,
    )
    username = extract_configuration_param(
        siemplify, provider_name=INTEGRATION_NAME, param_name="Username"
    )
    password = extract_configuration_param(
        siemplify, provider_name=INTEGRATION_NAME, param_name="Password"
    )
    api_token = extract_configuration_param(
        siemplify, provider_name=INTEGRATION_NAME, param_name="API Token"
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        print_value=True,
        input_type=bool,
    )
    ca_certificate = extract_configuration_param(
        siemplify, provider_name=INTEGRATION_NAME, param_name="CA Certificate File"
    )

    query = extract_action_param(
        siemplify, param_name="Query", print_value=True, is_mandatory=True
    )
    search_mode = extract_action_param(
        siemplify,
        param_name="Search Mode",
        print_value=True,
        is_mandatory=False,
        default_value="Smart",
    )

    result_fields = extract_action_param(
        siemplify, param_name="Result fields", print_value=True
    )
    ip_key = extract_action_param(
        siemplify, param_name="IP Entity Key", print_value=True
    )
    hostname_key = extract_action_param(
        siemplify, param_name="Hostname Entity Key", print_value=True
    )
    filehash_key = extract_action_param(
        siemplify, param_name="File Hash Entity Key", print_value=True
    )
    user_key = extract_action_param(
        siemplify, param_name="User Entity Key", print_value=True
    )
    url_key = extract_action_param(
        siemplify, param_name="URL Entity Key", print_value=True
    )
    email_key = extract_action_param(
        siemplify, param_name="Email Address Entity Key", print_value=True
    )
    stop_if_not_enough = extract_action_param(
        siemplify,
        param_name="Stop If Not Enough Entities",
        print_value=True,
        input_type=bool,
        is_mandatory=True,
    )
    limit = extract_action_param(
        siemplify,
        param_name="Results count limit",
        input_type=int,
        default_value=DEFAULT_QUERY_LIMIT,
        print_value=True,
    )

    suitable_entities = [
        entity
        for entity in siemplify.target_entities
        if entity.entity_type in SUITABLE_ENTITY_TYPES
    ]
    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    output_message = ""
    result_value = False
    status = EXECUTION_STATE_INPROGRESS

    try:
        suitable_entities_by_type, types_mapper = validate_entities(
            suitable_entities,
            ip_key,
            hostname_key,
            filehash_key,
            user_key,
            url_key,
            email_key,
        )

        missing_entity_keys = [
            types_mapper.get(key)
            for key, value in suitable_entities_by_type.items()
            if not value
        ]
        if stop_if_not_enough and bool(missing_entity_keys):
            raise MissingEntityKeysException(missing_entity_keys=missing_entity_keys)

        manager = SplunkManager(
            server_address=url,
            username=username,
            password=password,
            api_token=api_token,
            ca_certificate=ca_certificate,
            verify_ssl=verify_ssl,
            siemplify_logger=siemplify.LOGGER,
            force_check_connectivity=True,
        )

        if is_first_run:
            not_empty_suitable_entities_by_type = {
                key: value for key, value in suitable_entities_by_type.items() if value
            }
            output_message, result_value, status = start_operation(
                siemplify,
                manager=manager,
                search_mode=search_mode,
                query=query,
                suitable_entities=not_empty_suitable_entities_by_type,
                types_mapper=types_mapper,
                result_fields=result_fields,
                limit=limit,
            )

        if status == EXECUTION_STATE_INPROGRESS:
            result = (
                result_value
                if result_value
                else extract_action_param(
                    siemplify, param_name="additional_data", default_value="{}"
                )
            )
            output_message, result_value, status = query_operation_status(
                siemplify=siemplify,
                manager=manager,
                result=result,
                query=query,
                result_fields=result_fields,
                limit=limit,
            )

    except MissingEntityKeysException as err:

        output_message = (
            "Action wasn't able to build the query, "
            "because not enough entity types were supplied for "
            'the specified "{0} Entity Keys". '
            'Please disable "Stop If Not Enough Entities" parameter '
            "or provide at least one entity "
            'for each specified "{0} Entity Key".'.format(
                ", ".join(err.missing_entity_keys)
            )
        )
        result_value = False
        status = EXECUTION_STATE_COMPLETED
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(err)

    except AdhocSearchLevelException:
        output_message = (
            f"Error executing action {EXECUTE_ENTITY_QUERY_SCRIPT_NAME}."
            "Reason: Wrong input Search Mode"
        )
        status = EXECUTION_STATE_FAILED
        result_value = False
        siemplify.LOGGER.error(output_message)

    except Exception as e:
        output_message = (
            f"Error executing action {EXECUTE_ENTITY_QUERY_SCRIPT_NAME}. Reason: {e}"
        )
        status = EXECUTION_STATE_FAILED
        result_value = False
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  "
        f"results: {result_value}\n  "
        f"output_message: {output_message}"
    )

    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    is_first_run = len(sys.argv) < 3 or sys.argv[2] == "True"
    main(is_first_run)
