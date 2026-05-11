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
from ..core.FireEyeHelixManager import FireEyeHelixManager
from soar_sdk.SiemplifyUtils import output_handler, convert_dict_to_json_result_dict
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from TIPCommon import extract_configuration_param
from ..core.FireEyeHelixConstants import (
    PROVIDER_NAME,
    ENRICH_ENDPOINT_SCRIPT_NAME,
    ENRICHMENT_PREFIX,
)

SUPPORTED_ENTITY_TYPES = [EntityTypes.HOSTNAME]


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = ENRICH_ENDPOINT_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    # Configuration.
    api_root = extract_configuration_param(
        siemplify,
        provider_name=PROVIDER_NAME,
        param_name="API Root",
        is_mandatory=True,
        print_value=True,
    )

    api_token = extract_configuration_param(
        siemplify,
        provider_name=PROVIDER_NAME,
        param_name="API Token",
        is_mandatory=True,
        print_value=False,
    )

    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=PROVIDER_NAME,
        param_name="Verify SSL",
        input_type=bool,
        is_mandatory=True,
        print_value=True,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    status = EXECUTION_STATE_COMPLETED
    result_value = True
    output_messages = []
    json_results = {}
    successful_entities = []
    failed_entities = []
    suitable_entities = [
        entity
        for entity in siemplify.target_entities
        if entity.entity_type in SUPPORTED_ENTITY_TYPES
    ]

    try:
        manager = FireEyeHelixManager(
            api_root=api_root,
            api_token=api_token,
            verify_ssl=verify_ssl,
            siemplify=siemplify,
        )

        for entity in suitable_entities:
            siemplify.LOGGER.info(f"Started processing entity: {entity.identifier}")
            entity_object = manager.get_endpoint(entity.identifier)

            if entity_object:
                enrichment_data = entity_object.to_enrichment_data(
                    prefix=ENRICHMENT_PREFIX
                )
                entity.additional_properties.update(enrichment_data)
                entity.is_enriched = True

                # JSON result
                json_results[entity.identifier] = entity_object.to_json()
                siemplify.LOGGER.info(
                    f"Successfully enriched the following entity in FireEye Helix: {entity.identifier}"
                )
                successful_entities.append(entity)
            else:
                failed_entities.append(entity)

            siemplify.LOGGER.info(f"Finished processing entity {entity.identifier}")

        if successful_entities:
            siemplify.update_entities(successful_entities)
            siemplify.result.add_result_json(
                convert_dict_to_json_result_dict(json_results)
            )
            output_messages.append(
                "Successfully enriched the following entities in FireEye Helix: {}".format(
                    "\n".join([entity.identifier for entity in successful_entities])
                )
            )

        if failed_entities:
            output_messages.append(
                "Action was not able to enrich the following entities in FireEye Helix: {}".format(
                    "\n".join([entity.identifier for entity in failed_entities])
                )
            )

        output_message = "\n".join(output_messages)

        if not successful_entities:
            output_message = "No entities were enriched."
            result_value = False

    except Exception as e:
        output_message = f'Error executing action "Enrich Endpoint". Reason: {e}'
        result_value = False
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  is_success: {result_value}\n  output_message: {output_message}"
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
