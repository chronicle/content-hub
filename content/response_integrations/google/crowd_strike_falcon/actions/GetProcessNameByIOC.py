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
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyUtils import output_handler, convert_dict_to_json_result_dict
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED

from TIPCommon.extraction import extract_configuration_param, extract_action_param
from TIPCommon.transformation import construct_csv, string_to_multi_value

from crowd_strike_falcon.core.constants import (
    API_ROOT_DEFAULT,
    INTEGRATION_NAME,
    GET_PROCESS_NAME_BY_IOC_SCRIPT_NAME,
    PRODUCT_NAME,
    SUPPORTED_HASH_TYPES,
    TYPES_IOC_MAPPER,
)
from crowd_strike_falcon.core.CrowdStrikeManager import CrowdStrikeManager
from crowd_strike_falcon.core.utils import get_entity_original_identifier, get_hash_type, get_domain_from_entity


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = GET_PROCESS_NAME_BY_IOC_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Root",
        default_value=API_ROOT_DEFAULT,
    )
    client_id = extract_configuration_param(
        siemplify, provider_name=INTEGRATION_NAME, param_name="Client API ID"
    )
    client_secret = extract_configuration_param(
        siemplify, provider_name=INTEGRATION_NAME, param_name="Client API Secret"
    )
    use_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        input_type=bool,
        is_mandatory=True,
    )
    customer_id = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Customer ID",
        print_value=True,
    )
    device_names = string_to_multi_value(
        extract_action_param(siemplify, param_name="Devices Names", print_value=True)
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    result_value = True
    status = EXECUTION_STATE_COMPLETED
    successful_entities, failed_entities, json_results = [], [], {}

    try:
        manager = CrowdStrikeManager(
            client_id=client_id,
            client_secret=client_secret,
            use_ssl=use_ssl,
            api_root=api_root,
            customer_id=customer_id,
        )
        suitable_entities = [
            entity
            for entity in siemplify.target_entities
            if entity.entity_type in TYPES_IOC_MAPPER.keys()
        ]

        for entity in suitable_entities:
            result_per_entity = []
            entity_identifier = get_entity_original_identifier(entity)
            entity_type = TYPES_IOC_MAPPER[entity.entity_type]

            ioc_value = (
                entity_identifier
                if entity.entity_type != EntityTypes.URL
                else get_domain_from_entity(entity_identifier)
            )
            try:
                ioc_type = (
                    entity_type
                    if entity_type
                    else get_entity_hash_type(entity_identifier)
                )
            except Exception as e:
                siemplify.LOGGER.exception(e)
                siemplify.LOGGER.error(
                    f"Invalid hash type. Skip on entity: {entity_identifier}."
                )
                continue

            for device_name in device_names:
                try:
                    if not ioc_type or not ioc_value:
                        raise

                    result_per_entity.extend(
                        manager.get_processes_by_device_name(
                            device_name=device_name,
                            ioc_type=ioc_type,
                            ioc_value=ioc_value,
                        )
                    )
                except Exception as e:
                    failed_entities.append(entity_identifier)
                    siemplify.LOGGER.error(f"An error occurred on {ioc_value}")
                    siemplify.LOGGER.exception(e)

            if result_per_entity:
                json_results[entity_identifier] = [
                    result.to_json() for result in result_per_entity
                ]
                siemplify.result.add_entity_table(
                    entity_identifier,
                    construct_csv([result.to_csv() for result in result_per_entity]),
                )
                successful_entities.append(entity_identifier)
            else:
                failed_entities.append(entity_identifier)

        if successful_entities:
            siemplify.result.add_result_json(
                convert_dict_to_json_result_dict(json_results)
            )
            output_message = (
                "Successfully retrieved processes related to the IOCs on the following endpoints in "
                f'{PRODUCT_NAME}: {", ".join(successful_entities)}\n'
            )
            if failed_entities:
                output_message += (
                    f"No related processes were found on the following endpoints in {PRODUCT_NAME}:"
                    f'{", ".join(failed_entities)}\n'
                )
        else:
            result_value = False
            output_message = f"No related processes were found on the provided endpoints in {PRODUCT_NAME}."
    except Exception as e:
        output_message = (
            f"Error executing '{GET_PROCESS_NAME_BY_IOC_SCRIPT_NAME}'. Reason: {e}"
        )
        status = EXECUTION_STATE_FAILED
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
        result_value = False

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  is_success: {result_value}\n  output_message: {output_message}"
    )
    siemplify.end(output_message, result_value, status)


def get_entity_hash_type(entity_identifier):
    hash_type = get_hash_type(entity_identifier)
    if hash_type not in SUPPORTED_HASH_TYPES:
        raise

    return hash_type


if __name__ == "__main__":
    main()
