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
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyUtils import convert_dict_to_json_result_dict, output_handler
from TIPCommon import construct_csv, extract_configuration_param

from ..core.constants import ENRICH_ENTITIES_ACTION, INTEGRATION_NAME, PRODUCT_NAME
from ..core.IllusiveNetworksExceptions import RateLimitException
from ..core.IllusiveNetworksManager import IllusiveNetworksManager


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = ENRICH_ENTITIES_ACTION
    siemplify.LOGGER.info("================= Main - Param Init =================")

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
        is_mandatory=True,
        print_value=False,
    )
    ca_certificate = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="CA Certificate File",
        is_mandatory=False,
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        default_value=False,
        input_type=bool,
        is_mandatory=True,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    status = EXECUTION_STATE_COMPLETED
    result_value = True
    output_message = ""
    failed_entities = []
    json_results = {}
    entities_to_update = []

    scope_entities = [
        entity
        for entity in siemplify.target_entities
        if entity.entity_type == EntityTypes.HOSTNAME
    ]

    try:
        illusivenetworks_manager = IllusiveNetworksManager(
            api_root=api_root,
            api_key=api_key,
            ca_certificate=ca_certificate,
            verify_ssl=verify_ssl,
            siemplify_logger=siemplify.LOGGER,
        )
        illusivenetworks_manager.test_connectivity()
        for entity in scope_entities:
            try:
                host_object = illusivenetworks_manager.enrich_entity(
                    host_entity_name=entity.identifier
                )

                if not host_object.raw_data:
                    failed_entities.append(entity)
                    continue

                json_results[entity.identifier] = host_object.to_json()
                entity.is_enriched = True
                entity.additional_properties.update(host_object.as_enrichment_data())
                entities_to_update.append(entity)

                siemplify.result.add_entity_table(
                    f"{entity.identifier}",
                    construct_csv(host_object.to_table()),
                )

            except RateLimitException:
                raise
            except Exception as e:
                failed_entities.append(entity)
                siemplify.LOGGER.error(
                    f"An error occurred on entity: {entity.identifier}"
                )
                siemplify.LOGGER.exception(e)

        if len(scope_entities) == len(failed_entities):
            output_message += "No entities were enriched."
            result_value = False

        else:
            if entities_to_update:
                siemplify.update_entities(entities_to_update)
                output_message += (
                    "Successfully enriched the following entities using {}:\n{}".format(
                        PRODUCT_NAME,
                        "\n".join([entity.identifier for entity in entities_to_update]),
                    )
                )

                siemplify.result.add_result_json(
                    convert_dict_to_json_result_dict(json_results)
                )
            if failed_entities:
                output_message += "\nAction wasn't able to enrich the following entities using {}:\n{}".format(
                    PRODUCT_NAME,
                    "\n".join([entity.identifier for entity in failed_entities]),
                )

    except Exception as e:
        output_message += (f"Error executing action {ENRICH_ENTITIES_ACTION}. "
                           f"Reason: {e}.")
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
