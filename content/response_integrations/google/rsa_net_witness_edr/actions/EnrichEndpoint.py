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
from soar_sdk.SiemplifyAction import SiemplifyAction
from ..core.RSAManager import RSAManager
from ..core.RSAExceptions import MachineDoesntExistError
from TIPCommon import extract_configuration_param, extract_action_param
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyDataModel import EntityTypes
from ..core.constants import INTEGRATION_NAME, ENRICHENDPOINT_ACTION, ENRICHMENT_PREFIX

SUPPORTED_ENTITY_TYPES = [EntityTypes.ADDRESS, EntityTypes.HOSTNAME]


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = ENRICHENDPOINT_ACTION
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    api_root = extract_configuration_param(
        siemplify, provider_name=INTEGRATION_NAME, param_name="API Root"
    )
    username = extract_configuration_param(
        siemplify, provider_name=INTEGRATION_NAME, param_name="Username"
    )
    password = extract_configuration_param(
        siemplify, provider_name=INTEGRATION_NAME, param_name="Password"
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        default_value=True,
        input_type=bool,
        is_mandatory=True,
    )

    # Parameters
    iioc_score_threshold = extract_action_param(
        siemplify, param_name="IIOC Score Threshold", default_value=50, input_type=int
    )
    max_iocs_to_return = extract_action_param(
        siemplify, param_name="Max IOCs To Return", default_value=50, input_type=int
    )
    include_ioc_information = extract_action_param(
        siemplify,
        param_name="Include IOC Information",
        default_value=False,
        input_type=bool,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    status = EXECUTION_STATE_COMPLETED
    result_value = True
    successful_entities = []
    failed_entities = []
    output_message = ""
    json_results = {}
    suitable_entities = [
        entity
        for entity in siemplify.target_entities
        if entity.entity_type in SUPPORTED_ENTITY_TYPES
    ]

    if suitable_entities:
        try:
            rsa_manager = RSAManager(
                api_root=api_root,
                username=username,
                password=password,
                verify_ssl=verify_ssl,
            )

            for entity in suitable_entities:
                siemplify.LOGGER.info(f"Started processing entity: {entity.identifier}")

                try:
                    entity_object = rsa_manager.enrich_endpoint(
                        entity_id=entity.identifier, entity_type=entity.entity_type
                    )
                    if include_ioc_information:
                        iocs_object = rsa_manager.get_endpoint_iocs(
                            entity_id=entity.identifier,
                            entity_type=entity.entity_type,
                            max_iocs_to_return=max_iocs_to_return,
                        )

                    if entity_object:
                        enrichment_data = entity_object.to_enrichment_data(
                            prefix=ENRICHMENT_PREFIX
                        )
                        entity.additional_properties.update(enrichment_data)
                        entity.is_enriched = True
                        object_json = entity_object.to_json()

                        if (
                            iioc_score_threshold
                            and int(entity_object.iioc_score) > iioc_score_threshold
                        ):
                            entity.is_suspicious = True

                        # If both objects were requested, JSONs are combined
                        if include_ioc_information and iocs_object:
                            object_json = {**entity_object.to_json(), **iocs_object}

                        # JSON result
                        json_results[entity.identifier] = object_json
                        successful_entities.append(entity)
                    else:
                        failed_entities.append(entity)

                    siemplify.LOGGER.info(
                        f"Finished processing entity {entity.identifier}"
                    )

                except MachineDoesntExistError as e:
                    failed_entities.append(entity)
                    siemplify.LOGGER.info(
                        f"Failed processing entity {entity.identifier}. Reason: {e}"
                    )
                    pass

        except Exception as e:
            output_message = (
                f"Error executing action {ENRICHENDPOINT_ACTION}. Reason: {e}"
            )
            siemplify.LOGGER.error(output_message)
            siemplify.LOGGER.exception(e)
            status = EXECUTION_STATE_FAILED
            result_value = False

    if successful_entities:
        siemplify.update_entities(successful_entities)
        siemplify.result.add_result_json(convert_dict_to_json_result_dict(json_results))
        output_message = "Successfully enriched the following endpoints from RSA Netwitness EDR: {}".format(
            "\n".join([entity.identifier for entity in successful_entities])
        )
        siemplify.LOGGER.info(
            "Successfully enriched the following endpoints from RSA Netwitness EDR: {}".format(
                "\n".join([entity.identifier for entity in successful_entities])
            )
        )

    if failed_entities:
        output_message += "Action was not able to enrich the following endpoints from RSA Netwitness EDR: {}".format(
            "\n".join([entity.identifier for entity in failed_entities])
        )
        siemplify.LOGGER.info(
            "Action was not able to enrich the following endpoints from RSA Netwitness EDR: {}".format(
                "\n".join([entity.identifier for entity in failed_entities])
            )
        )

    if not successful_entities:
        output_message = "No entities were enriched."
        result_value = False

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  result_value: {result_value}\n  output_message: {output_message}"
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
