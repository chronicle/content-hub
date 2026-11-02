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

from crowd_strike_falcon.core.constants import (
    API_ROOT_DEFAULT,
    HASHES,
    HOSTS,
    INTEGRATION_NAME,
    IP_ADDRESSES,
    PRODUCT_NAME,
    UPDATE_IOC_INFORMATION_SCRIPT_NAME,
    URLS,
)
from crowd_strike_falcon.core.CrowdStrikeManager import CrowdStrikeManager
from crowd_strike_falcon.core.utils import (
    calculate_date,
    get_domain_from_entity,
    get_entity_original_identifier,
    get_existing_list,
)


ENTITY_TYPE_WITH_KEY_MAPPING = {
    EntityTypes.HOSTNAME: HOSTS,
    EntityTypes.ADDRESS: IP_ADDRESSES,
    EntityTypes.URL: URLS,
    EntityTypes.FILEHASH: HASHES,
}

SUPPORTED_ENTITY_TYPES = list(ENTITY_TYPE_WITH_KEY_MAPPING.keys())


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = UPDATE_IOC_INFORMATION_SCRIPT_NAME

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
    customer_id=extract_configuration_param(
        siemplify, provider_name=INTEGRATION_NAME, param_name="Customer ID"
    )

    description = extract_action_param(
        siemplify, param_name="Description", print_value=True
    )
    source = extract_action_param(siemplify, param_name="Source", print_value=True)
    expiration_days = extract_action_param(
        siemplify, param_name="Expiration days", print_value=True, input_type=int
    )
    detect_policy = extract_action_param(
        siemplify, param_name="Detect policy", print_value=True, input_type=bool
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
        suitable_entities = {
            get_entity_original_identifier(entity): entity
            for entity in siemplify.target_entities
            if entity.entity_type in SUPPORTED_ENTITY_TYPES
        }

        entities_with_keys = {key: [] for key in ENTITY_TYPE_WITH_KEY_MAPPING.values()}
        for entity_identifier, entity in suitable_entities.items():
            get_existing_list(
                entities_with_keys, ENTITY_TYPE_WITH_KEY_MAPPING[entity.entity_type]
            ).append(entity_identifier)

        for entity_type, entities in entities_with_keys.items():
            for entity_identifier in entities:
                ioc_value = (
                    entity_identifier
                    if entity_type != URLS
                    else get_domain_from_entity(entity_identifier)
                )
                ioc_value = ioc_value.lower()
                try:
                    if not ioc_value:
                        raise

                    id_list = manager.get_ioc_id(ioc_value=ioc_value)
                    if not id_list:
                        raise Exception(f"Failed to get ID for {ioc_value} IOC.")

                    ioc_details = manager.get_iocs(id_list)

                    if not ioc_details:
                        raise Exception(f"Failed to get details for {ioc_value} IOC.")

                    resources = manager.update_ioc(
                        ioc_id=id_list[0],
                        expiration_date=(
                            calculate_date(days=expiration_days)
                            if expiration_days
                            else None
                        ),
                        detect_policy=detect_policy,
                        source=source,
                        description=description,
                        severity=ioc_details[0].severity,
                    )

                    if resources:
                        json_results[entity_identifier] = resources[0]
                        successful_entities.append(entity_identifier)

                except Exception as e:
                    failed_entities.append(entity_identifier)
                    siemplify.LOGGER.error(
                        f"An error occurred on entity: {entity_identifier}. {e}."
                    )
                    siemplify.LOGGER.exception(e)

        if successful_entities:
            output_message = (
                f"Successfully updated the following entities in {PRODUCT_NAME}: "
                f'{", ".join(successful_entities)}\n'
            )
            siemplify.result.add_result_json(
                convert_dict_to_json_result_dict(json_results)
            )

            if failed_entities:
                output_message += (
                    f"Action wasn't able to update the following entities in {PRODUCT_NAME}: "
                    f'{", ".join(failed_entities)}\n'
                )
        else:
            result_value = False
            output_message = f"No entities were updated in {PRODUCT_NAME}."

    except Exception as e:
        output_message = f"Error executing action '{UPDATE_IOC_INFORMATION_SCRIPT_NAME}'. Reason: {e}"
        status = EXECUTION_STATE_FAILED
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
        result_value = False

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  is_success: {result_value}\n  output_message: {output_message}"
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
