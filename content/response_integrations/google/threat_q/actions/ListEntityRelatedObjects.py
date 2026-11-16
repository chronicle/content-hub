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
from soar_sdk.SiemplifyUtils import (
    output_handler,
    add_prefix_to_dict_keys,
    convert_dict_to_json_result_dict,
)
from soar_sdk.SiemplifyAction import SiemplifyAction
from TIPCommon import extract_configuration_param, extract_action_param, construct_csv
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED

from ..core.ThreatQManager import ThreatQManager

from ..core.constants import (
    INTEGRATION_NAME,
    LIST_ENTITY_RELATED_OBJECTS_SCRIPT,
    THREATQ_PREFIX,
)

from ..core.custom_exceptions import ThreatQManagerException


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = LIST_ENTITY_RELATED_OBJECTS_SCRIPT

    siemplify.LOGGER.info("=" * 10 + " Main - Param Init " + "=" * 10)

    server_address = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="ServerAddress",
        input_type=str,
    )

    client_id = extract_configuration_param(
        siemplify, provider_name=INTEGRATION_NAME, param_name="ClientId", input_type=str
    )

    username = extract_configuration_param(
        siemplify, provider_name=INTEGRATION_NAME, param_name="Username", input_type=str
    )

    password = extract_configuration_param(
        siemplify, provider_name=INTEGRATION_NAME, param_name="Password", input_type=str
    )

    related_object_type = extract_action_param(
        siemplify,
        param_name="Related Object Type",
        default_value="Adversary",
        is_mandatory=True,
        print_value=True,
    )

    limit = extract_action_param(
        siemplify,
        param_name="Max Related Objects To Return",
        input_type=int,
        default_value=50,
        is_mandatory=False,
        print_value=True,
    )

    siemplify.LOGGER.info("=" * 10 + " Main - Started " + "=" * 10)
    successful_entities = []
    failed_entities = []
    json_results = {}
    result_value = False
    execution_status = EXECUTION_STATE_COMPLETED
    output_message = ""

    try:
        threatq_manager = ThreatQManager(server_address, client_id, username, password)

        for entity in siemplify.target_entities:
            siemplify.LOGGER.info(f"Started processing entity: {entity.identifier}")
            try:
                related_objects = threatq_manager.get_entity_related_objects(
                    related_object_type=related_object_type,
                    indicator=entity.identifier,
                    limit=limit,
                )
                siemplify.LOGGER.info(
                    f"Found {len(related_objects)} related objects for entity: {entity.identifier}"
                )
                if related_objects:
                    successful_entities.append(entity)
                    json_results[entity.identifier] = [
                        related_object.to_json() for related_object in related_objects
                    ]

                    siemplify.result.add_entity_table(
                        f"Related {related_object_type} objects for {entity.identifier}",
                        construct_csv(
                            [
                                related_object.to_table()
                                for related_object in related_objects
                            ]
                        ),
                    )
                    for i, related_object in enumerate(related_objects):
                        entity.additional_properties.update(
                            add_prefix_to_dict_keys(
                                related_object.to_flat_dict(index=i), THREATQ_PREFIX
                            )
                        )
                    entity.is_enriched = True
                else:
                    failed_entities.append(entity)

            except ThreatQManagerException as e:
                siemplify.LOGGER.info(e)
                failed_entities.append(entity)

            siemplify.LOGGER.info(f"Finished processing entity: {entity.identifier}")

        if successful_entities:
            siemplify.update_entities(successful_entities)
            siemplify.result.add_result_json(
                convert_dict_to_json_result_dict(json_results)
            )
            output_message = "Successfully listed related {} objects in ThreatQ for the following entities: {}".format(
                related_object_type,
                "\n".join([entity.identifier for entity in successful_entities]),
            )
            result_value = True

        if failed_entities:
            output_message += (
                "\n\nAction was not able to list related {} objects in ThreatQ for the following "
                "entities: {}".format(
                    related_object_type,
                    "\n".join([entity.identifier for entity in failed_entities]),
                )
            )

        if not successful_entities:
            output_message = "No related objects were listed."

    except Exception as e:
        output_message = (
            f'Error executing action "List Entity Related Objects". Reason: {e}'
        )
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
        execution_status = EXECUTION_STATE_FAILED

    siemplify.LOGGER.info("=" * 10 + " Main - Finished " + "=" * 10)
    siemplify.LOGGER.info(
        f"Status: {execution_status}, Result Value: {result_value}, Output Message: {output_message}"
    )
    siemplify.end(output_message, result_value, execution_status)


if __name__ == "__main__":
    main()
