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
import json
import sys
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyDataModel import EntityTypes
from ..core.CiscoOrbitalManager import CiscoOrbitalManager
from soar_sdk.SiemplifyUtils import output_handler, unix_now
from soar_sdk.ScriptResult import (
    EXECUTION_STATE_COMPLETED,
    EXECUTION_STATE_FAILED,
    EXECUTION_STATE_INPROGRESS,
)
from TIPCommon import extract_configuration_param, extract_action_param, construct_csv
from ..core.constants import PROVIDER_NAME, EXECUTE_QUERY_SCRIPT_NAME, MAX_EXPIRATION_IN_HOURS
from ..core.exceptions import BadRequestException
from ..core.UtilsManager import is_action_approaching_timeout, hours_to_milliseconds

SUPPORTED_ENTITY_TYPES = [EntityTypes.ADDRESS, EntityTypes.HOSTNAME]
ITERATIONS_LIMIT = 2


def start_operation(
    siemplify,
    manager,
    entities,
    query,
    name,
    context,
    limit,
    hide_case_wall_table,
    expiration_unix,
):
    """
    Submit the query on endpoints.
    :param siemplify: SiemplifyAction object.
    :param manager: CiscoOrbitalManager object.
    :param entities: {list} The list of entities.
    :param query: {str} The query that needs to be executed.
    :param name: {str} The name for the query job.
    :param context: {str} The additional custom context fields that should be added to the job.
    :param limit: {int} Maximum number of results rows.
    :param hide_case_wall_table: {bool} Whether hide case wall table or no.
    :param expiration_unix: {int} Unix epoch time the query will expire
    :return: {tuple} output messages, result value, status
    """
    job_id = manager.submit_query(entities, query, name, context, expiration_unix)
    # If api return job data almost instantly here we will try to get data.
    return query_operation_status(
        siemplify, manager, entities, job_id, limit, hide_case_wall_table
    )


def query_operation_status(
    siemplify, manager, entities, job_id, limit, hide_case_wall_table
):
    """
    Get endpoints query results.
    :param siemplify: SiemplifyAction object.
    :param manager: CiscoOrbitalManager object.
    :param entities: {list} The list of entities.
    :param job_id: {str} The job id to fetch data.
    :param limit: {int} Maximum number of results rows.
    :param hide_case_wall_table: {bool} Whether hide case wall table or no.
    :return: {tuple} output messages, result value, status
    """
    result_value = False
    output_messages = ""
    status = EXECUTION_STATE_INPROGRESS

    results = manager.get_endpoints_results(job_id, limit)
    successful_entities, pending_entities, failed_entities = check_entities_status(
        results, entities
    )
    reached_global_timeout = is_action_approaching_timeout(
        siemplify.execution_deadline_unix_time_ms
    )

    if pending_entities and not reached_global_timeout:
        output_messages = "Submitted Query. Waiting for results until timeout."
        entities_identifiers = [entity.identifier for entity in entities]
        result_value = json.dumps([job_id, entities_identifiers])
    else:
        if reached_global_timeout:
            siemplify.LOGGER.info(
                "Reached action's timeout. All pending entities will be considered as "
                "failed. Please consider increasing action's timeout from the IDE."
            )
        failed_entities.extend(pending_entities)

        if successful_entities:
            output_messages += (
                "Successfully executed query and retrieved results from Cisco Orbital "
                "on the following entities:\n{}".format(
                    "\n".join([item.get("identifier") for item in successful_entities])
                )
            )
            result_value = True
            siemplify.result.add_result_json(
                [item.get("result").to_json() for item in successful_entities]
            )

            if not hide_case_wall_table:
                for item in successful_entities:
                    for data in item.get("result").to_tables():
                        table_title = (
                            f"Results for {item.get('identifier')}"
                            if item.get("type") == EntityTypes.HOSTNAME
                            else f"Results for {item.get('identifier')} "
                                 f"({item.get('result').hostname})"
                        )

                        siemplify.result.add_data_table(
                            title=table_title, data_table=construct_csv(data)
                        )
        if failed_entities:
            output_messages += (
                "\nAction wasn't able to successfully execute query and retrieve "
                "results from Cisco Orbital on the following entities:\n{}".format(
                    "\n".join([entity.identifier for entity in failed_entities])
                )
            )

        if not successful_entities:
            result_value = False
            output_messages += (
                "\nAction wasn't able to execute queries on all provided entities in "
                "Cisco Orbital.\nPossible Reasons:\n   1. The query contains errors. "
                "Please check the query's syntax and try again.\n   2. The action "
                "timed out while waiting for results from Cisco Orbital. "
                "Please increase the action's timeout on the IDE and try again."
            )

        status = EXECUTION_STATE_COMPLETED

    return output_messages, result_value, status


@output_handler
def main(is_first_run):
    siemplify = SiemplifyAction()
    siemplify.script_name = EXECUTE_QUERY_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    api_root = extract_configuration_param(
        siemplify,
        provider_name=PROVIDER_NAME,
        param_name="API Root",
        is_mandatory=True,
        print_value=True
    )
    client_id = extract_configuration_param(
        siemplify,
        provider_name=PROVIDER_NAME,
        param_name="Client ID",
        is_mandatory=True,
        print_value=True,
    )
    client_secret = extract_configuration_param(
        siemplify,
        provider_name=PROVIDER_NAME,
        param_name="Client Secret",
        is_mandatory=True,
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=PROVIDER_NAME,
        param_name="Verify SSL",
        is_mandatory=True,
        input_type=bool,
    )

    query = extract_action_param(
        siemplify, param_name="Query", is_mandatory=True, print_value=True
    )
    name = extract_action_param(siemplify, param_name="Name")
    custom_context_fields = extract_action_param(
        siemplify, param_name="Custom Context Fields"
    )
    max_results_to_return = extract_action_param(
        siemplify, param_name="Max Results To Return", input_type=int
    )
    hide_case_wall_table = extract_action_param(
        siemplify, param_name="Hide Case Wall Table", input_type=bool
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    try:
        manager = CiscoOrbitalManager(
            api_root=api_root,
            client_id=client_id,
            client_secret=client_secret,
            verify_ssl=verify_ssl,
            siemplify_logger=siemplify.LOGGER,
        )

        if is_first_run:
            expiration_unix = siemplify.execution_deadline_unix_time_ms
            min_expiration = unix_now() + 60 * 1000
            max_expiration = unix_now() + hours_to_milliseconds(MAX_EXPIRATION_IN_HOURS)
            if expiration_unix > max_expiration:
                siemplify.LOGGER.info(
                    "Timeout value provided in the IDE exceeds maximum allowed value "
                    "of 24 hours. Using maximum value of 24 hours"
                )
                expiration_unix = max_expiration // 1000
            elif expiration_unix < min_expiration:
                siemplify.LOGGER.info(
                    "Timeout value provided in the IDE is lower than allowed value of "
                    "1 minute. Using minimum value of 1 minute"
                )
                expiration_unix = min_expiration // 1000
            else:
                expiration_unix = expiration_unix // 1000
            suitable_entities = [
                entity
                for entity in siemplify.target_entities
                if entity.entity_type in SUPPORTED_ENTITY_TYPES
            ]
            output_messages, result_value, status = start_operation(
                siemplify,
                manager,
                suitable_entities,
                query,
                name,
                custom_context_fields,
                max_results_to_return,
                hide_case_wall_table,
                expiration_unix,
            )
        else:
            job_id, entities_identifiers = json.loads(
                siemplify.parameters["additional_data"]
            )
            suitable_entities = [
                entity
                for entity in siemplify.target_entities
                if entity.identifier in entities_identifiers
            ]
            output_messages, result_value, status = query_operation_status(
                siemplify,
                manager,
                suitable_entities,
                job_id,
                max_results_to_return,
                hide_case_wall_table,
            )

    except BadRequestException as e:
        result_value = False
        status = EXECUTION_STATE_COMPLETED
        output_messages = (
            f"Action wasn't able to execute queries in Cisco Orbital. Reason: {e}"
        )
        siemplify.LOGGER.error(output_messages)
        siemplify.LOGGER.exception(e)
    except Exception as e:
        siemplify.LOGGER.error(
            f"General error performing action {EXECUTE_QUERY_SCRIPT_NAME}"
        )
        siemplify.LOGGER.exception(e)
        result_value = False
        status = EXECUTION_STATE_FAILED
        output_messages = f'Error executing action "Execute Query". Reason: {e}'

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"Result: {result_value}")
    siemplify.LOGGER.info(f"Output Messages: {output_messages}")

    siemplify.end(output_messages, result_value, status)


def check_entities_status(results, entities):
    """
    Get processed entities status
    :param results: {list} List of EndpointResult objects.
    :param entities: {list} The list of entities.
    :return: {tuple} successful entities and results, pending entities, failed entities
    """
    successful_entities, pending_entities, failed_entities = [], [], []

    if not results:
        pending_entities = entities
    else:
        for entity in entities:
            for result in results:
                if (
                    entity.entity_type == EntityTypes.HOSTNAME
                    and entity.identifier == result.hostname
                ) or (
                    entity.entity_type == EntityTypes.ADDRESS
                    and is_address_in_result(entity, result)
                ):
                    if not result.error:
                        successful_entities.append(
                            {
                                "identifier": entity.identifier,
                                "type": entity.entity_type,
                                "result": result,
                            }
                        )
                    else:
                        failed_entities.append(entity)
                else:
                    pending_entities.append(entity)

    return successful_entities, pending_entities, failed_entities


def is_address_in_result(entity, result):
    """
    Check if address entity exists in result
    :param entity: The entity
    :param result: EndpointResult object
    :return: {bool} True if exists, False otherwise
    """
    return (
        [entity.identifier for ip in result.local_ipv4 if entity.identifier in ip]
        or [entity.identifier for ip in result.local_ipv6 if entity.identifier in ip]
        or (result.external_ipv4 and entity.identifier in result.external_ipv4)
    )


if __name__ == "__main__":
    is_first_run = len(sys.argv) < 3 or sys.argv[2] == "True"
    main(is_first_run)
