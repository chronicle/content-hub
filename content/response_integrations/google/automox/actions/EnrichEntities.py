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
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import convert_dict_to_json_result_dict
from soar_sdk.SiemplifyUtils import output_handler
from TIPCommon import (
    extract_configuration_param,
    extract_action_param,
    flat_dict_to_csv,
)

from ..core.AutomoxManager import AutomoxManager
from ..core.constants import (
    INTEGRATION_NAME,
    ENRICH_ENTITIES_SCRIPT_NAME,
    SUPPORTED_ENTITIES,
    ENTITY_MAPPER,
)
from ..core.AutomoxUtils import get_entity_original_identifier


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = ENRICH_ENTITIES_SCRIPT_NAME

    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Root",
        is_mandatory=True,
        print_value=True,
    )
    api_key = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Key",
        remove_whitespaces=False,
        is_mandatory=True,
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        input_type=bool,
        is_mandatory=True,
        print_value=True,
    )

    return_patches = extract_action_param(
        siemplify, param_name="Return Patches", input_type=bool, print_value=True
    )
    max_patches_to_return = extract_action_param(
        siemplify, param_name="Max Patches To Return", input_type=int, print_value=True
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    result_value = True
    status = EXECUTION_STATE_COMPLETED
    successful_entities, failed_entities, json_results = [], [], {}

    suitable_entities = [
        entity
        for entity in siemplify.target_entities
        if entity.entity_type in SUPPORTED_ENTITIES
    ]

    try:
        if return_patches and max_patches_to_return <= 0:
            raise ValueError("Max Patches To Return must be a positive integer")

        manager = AutomoxManager(
            api_root=api_root, api_key=api_key, verify_ssl=verify_ssl
        )

        siemplify.LOGGER.info(f"Enriching devices from Automox")
        for entity in suitable_entities:
            entity_original_identifier = get_entity_original_identifier(entity)

            devices = manager.get_devices(
                filter_value=entity_original_identifier,
                filter_field=ENTITY_MAPPER[entity.entity_type],
                include_details=1,
            )

            if not devices:
                siemplify.LOGGER.info(
                    f"Entity {entity.identifier} wasn't found on Automox"
                )
                failed_entities.append(entity)
                continue

            device = devices[0]
            siemplify.LOGGER.info(
                f"Fetched device with id {device.id} for entity "
                f"{entity.identifier} from Automox"
            )

            device_data = device.as_enrichment_data()
            entity.additional_properties.update(device_data)
            siemplify.result.add_entity_table(
                entity.identifier, flat_dict_to_csv(device.as_table())
            )

            entity.is_enriched = True
            successful_entities.append(entity)

            json_payload = device.as_json()

            if return_patches:
                siemplify.LOGGER.info(
                    f"Fetching patches for device with id {device.id} from Automox"
                )
                patches = manager.get_patches(
                    device_id=device.id, max_patches=max_patches_to_return
                )
                json_payload["list_of_patches"] = [patch.as_json() for patch in patches]

            json_results[entity.identifier] = json_payload

        if successful_entities:
            output_message = (
                f"Successfully enriched the following entities using information from Automox: "
                f'{", ".join(entity.identifier for entity in successful_entities)}\n'
            )
            siemplify.LOGGER.info(output_message)
            siemplify.update_entities(successful_entities)
            siemplify.result.add_result_json(
                convert_dict_to_json_result_dict(json_results)
            )

            if failed_entities:
                log_message = (
                    f"Action wasn’t able to enrich the following entities using information from Automox "
                    f'{", ".join(entity.identifier for entity in failed_entities)}\n'
                )
                output_message += log_message
                siemplify.LOGGER.info(log_message)
        else:
            result_value = False
            output_message = "None of the provided entities were enriched."
            siemplify.LOGGER.info(output_message)

    except Exception as e:
        output_message = (
            f"Error executing action '{ENRICH_ENTITIES_SCRIPT_NAME}'. Reason: {e}"
        )
        status = EXECUTION_STATE_FAILED
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
        result_value = False

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}"
        f"\n  is_success: {result_value}"
        f"\n  output_message: {output_message}"
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
