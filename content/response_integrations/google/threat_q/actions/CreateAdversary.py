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
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyUtils import (
    output_handler,
    add_prefix_to_dict_keys,
    convert_dict_to_json_result_dict,
)
from soar_sdk.SiemplifyAction import SiemplifyAction
from TIPCommon import extract_configuration_param
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED

from ..core.ThreatQManager import ThreatQManager
from ..core.custom_exceptions import ThreatQManagerException
from ..core.constants import INTEGRATION_NAME, INTEGRATION_PREFIX, CREATE_ADVERSARY_SCRIPT


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = CREATE_ADVERSARY_SCRIPT

    json_results = {}
    entities_to_update = []
    failed_entities = []
    output_messages = []

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

    siemplify.LOGGER.info("=" * 10 + " Main - Started " + "=" * 10)

    scope_entities = [
        entity
        for entity in siemplify.target_entities
        if entity.entity_type == EntityTypes.USER
    ]

    try:
        threatq_manager = ThreatQManager(server_address, client_id, username, password)
        for entity in scope_entities:
            try:
                siemplify.LOGGER.info(f"Started processing entity: {entity.identifier}")
                adversary = threatq_manager.create_adversary(name=entity.identifier)

                if not adversary:
                    siemplify.LOGGER.info(
                        f"Adversary {entity.identifier} was not created"
                    )
                    failed_entities.append(entity)
                    continue

                json_results[entity.identifier] = adversary.to_json()
                entity.additional_properties.update(
                    add_prefix_to_dict_keys(
                        adversary.to_flat_dict(), INTEGRATION_PREFIX
                    )
                )
                entities_to_update.append(entity)

            except Exception as e:
                failed_entities.append(entity)
                siemplify.LOGGER.error(f"Failed processing entity: {entity.identifier}")
                siemplify.LOGGER.exception(e)

        if entities_to_update:
            siemplify.update_entities(entities_to_update)
            siemplify.result.add_result_json(
                convert_dict_to_json_result_dict(json_results)
            )
            output_messages.append(
                f'Successfully created adversaries in ThreatQ based on the following entities: {", ".join([entity.identifier for entity in entities_to_update])}'
            )

            if failed_entities:
                output_messages.append(
                    f'Action was not able to create adversaries in ThreatQ based on the following entities: {", ".join([entity.identifier for entity in failed_entities])}'
                )

            result_value = True

        else:
            output_messages.append("No adversaries were created.")
            result_value = False

        output_message = "\n".join(output_messages)
        execution_status = EXECUTION_STATE_COMPLETED

    except (ThreatQManagerException, Exception) as e:
        output_message = f'Error executing action "Create Adversary"." Reason: {e}'
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
        execution_status = EXECUTION_STATE_FAILED
        result_value = False

    siemplify.LOGGER.info("=" * 10 + " Main - Finished " + "=" * 10)
    siemplify.LOGGER.info(
        f"Status: {execution_status}, Result Value: {result_value}, Output Message: {output_message}"
    )
    siemplify.end(output_message, result_value, execution_status)


if __name__ == "__main__":
    main()
