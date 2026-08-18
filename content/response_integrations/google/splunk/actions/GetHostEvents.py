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
from soar_sdk.SiemplifyUtils import output_handler, convert_dict_to_json_result_dict
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyAction import SiemplifyAction
from ..core.SplunkManager import SplunkManager
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from TIPCommon.extraction import extract_configuration_param, extract_action_param
from TIPCommon.transformation import construct_csv
from ..core.UtilsManager import get_entity_original_identifier
from ..core.exceptions import SplunkBadRequestException
from ..core.constants import (
    INTEGRATION_NAME,
    GET_HOST_EVENTS_SCRIPT_NAME,
    DEFAULT_QUERY_LIMIT,
    FROM_TIME_DEFAULT,
    TO_TIME_DEFAULT,
    HOST_KEY,
)


@output_handler
def main():
    siemplify = SiemplifyAction()

    siemplify.script_name = GET_HOST_EVENTS_SCRIPT_NAME

    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

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

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    limit = extract_action_param(
        siemplify,
        param_name="Event Per Host Limit",
        input_type=int,
        default_value=DEFAULT_QUERY_LIMIT,
        print_value=True,
        is_mandatory=True,
    )
    from_time = extract_action_param(
        siemplify,
        param_name="Results From",
        default_value=FROM_TIME_DEFAULT,
        print_value=True,
        is_mandatory=True,
    )
    to_time = extract_action_param(
        siemplify,
        param_name="Results To",
        default_value=TO_TIME_DEFAULT,
        print_value=True,
        is_mandatory=True,
    )
    result_fields = extract_action_param(
        siemplify, param_name="Result fields", print_value=True
    )
    index = extract_action_param(siemplify, param_name="Index", print_value=True)
    host_key = extract_action_param(
        siemplify, param_name="Host Key", default_value=HOST_KEY, print_value=True
    )

    result_value = True
    status = EXECUTION_STATE_COMPLETED
    result_json = {}
    successful_entities, failed_entities = [], []
    host_entities = [
        entity
        for entity in siemplify.target_entities
        if entity.entity_type == EntityTypes.HOSTNAME
    ]

    try:
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

        for entity in host_entities:
            entity_identifier = get_entity_original_identifier(entity)
            try:
                if index:
                    query = f'index="{index}" | where {host_key}="{entity_identifier}"'
                else:
                    query = f'{host_key}="{entity_identifier}"'

                events = manager.search_host_events(
                    query=query,
                    limit=limit,
                    from_time=from_time,
                    to_time=to_time,
                    fields=result_fields,
                )
                if not events:
                    failed_entities.append(entity)
                    continue

                json_output = [event.to_json() for event in events]
                csv_output = [event.to_csv(result_fields) for event in events]
                successful_entities.append(entity)
                siemplify.result.add_entity_table(
                    entity.identifier, construct_csv(csv_output)
                )
                result_json[entity_identifier] = json_output

            except Exception as e:
                if isinstance(e, SplunkBadRequestException):
                    raise
                failed_entities.append(entity)
                siemplify.LOGGER.error(
                    f"An error occurred on entity: {entity_identifier}.\n{e}."
                )
                siemplify.LOGGER.exception(e)

        if successful_entities:
            siemplify.result.add_result_json(
                convert_dict_to_json_result_dict(result_json)
            )
            output_message = (
                "Successfully returned events for the following hosts "
                f"in {INTEGRATION_NAME}: \n"
                + "\n".join([entity.identifier for entity in successful_entities])
            )

            if failed_entities:
                output_message += (
                    "\nNo events were found for the following hosts "
                    f"in {INTEGRATION_NAME}:\n"
                    + "\n".join([entity.identifier for entity in failed_entities])
                )
        else:
            result_value = False
            output_message = (
                f"No events were found for the provided hosts in {INTEGRATION_NAME}."
            )

    except Exception as e:
        output_message = (
            f"Error executing action '{GET_HOST_EVENTS_SCRIPT_NAME}'. Reason: {e}"
        )
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        result_value = False

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  "
        f"result_value: {result_value}\n  "
        f"output_message: {output_message}"
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
