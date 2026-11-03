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
from TIPCommon import extract_configuration_param, extract_action_param
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyDataModel import EntityTypes
from threat_q.core.ThreatQManager import ThreatQManager
import re

from threat_q.core.constants import (
    INTEGRATION_NAME,
    LINK_ENTITIES_TO_OBJECTS_SCRIPT,
    EMAIL_REGEX,
    OBJECT_TYPE_MAPPING,
)

from threat_q.core.custom_exceptions import ObjectNotFoundException

ENTITY_INDICATORS = [
    EntityTypes.CVE,
    EntityTypes.ADDRESS,
    EntityTypes.URL,
    EntityTypes.FILEHASH,
    EntityTypes.USER,
]


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = LINK_ENTITIES_TO_OBJECTS_SCRIPT
    siemplify.LOGGER.info("=" * 10 + " Main - Param Init " + "=" * 10)

    server_address = extract_configuration_param(
        siemplify, provider_name=INTEGRATION_NAME, param_name="ServerAddress"
    )

    client_id = extract_configuration_param(
        siemplify, provider_name=INTEGRATION_NAME, param_name="ClientId"
    )

    username = extract_configuration_param(
        siemplify, provider_name=INTEGRATION_NAME, param_name="Username"
    )

    password = extract_configuration_param(
        siemplify, provider_name=INTEGRATION_NAME, param_name="Password"
    )

    object_type = extract_action_param(
        siemplify,
        param_name="Object Type",
        default_value="Adversary",
        is_mandatory=True,
        print_value=True,
    )

    object_identifier = extract_action_param(
        siemplify, param_name="Object Identifier", is_mandatory=True, print_value=True
    )

    indicator_type = extract_action_param(
        siemplify,
        param_name="Indicator Type",
        default_value="ASN",
        is_mandatory=False,
        print_value=True,
    )

    siemplify.LOGGER.info("=" * 10 + " Main - Started " + "=" * 10)
    result_value = False
    execution_status = EXECUTION_STATE_COMPLETED
    output_message = ""
    successful_entities = []
    json_results = {}
    objects_to_link = {}

    try:
        threatq_manager = ThreatQManager(server_address, client_id, username, password)
        source_object_type = OBJECT_TYPE_MAPPING.get(object_type)
        source_object_id = threatq_manager.get_object_id(
            object_type=source_object_type,
            identifier=object_identifier,
            indicator_type=indicator_type,
            object_exception=ObjectNotFoundException,
        )

        for entity in siemplify.target_entities:
            siemplify.LOGGER.info(f"Started processing entity: {entity.identifier}")

            if entity.entity_type in ENTITY_INDICATORS or re.search(
                EMAIL_REGEX, entity.identifier
            ):
                try:
                    entity_indicator_id = threatq_manager.get_indicator_id(
                        entity.identifier
                    )
                    objects_to_link[entity_indicator_id] = "indicators"
                except Exception as e:
                    pass

            if entity.entity_type == EntityTypes.FILEHASH:
                try:
                    entity_malware_id = threatq_manager.get_malware_id(
                        entity.identifier
                    )
                    objects_to_link[entity_malware_id] = "malware"
                except Exception as e:
                    pass

            if entity.entity_type == EntityTypes.USER:

                try:
                    entity_adversary_id = threatq_manager.get_adversary_id(
                        entity.identifier
                    )
                    objects_to_link[entity_adversary_id] = "adversaries"
                except Exception as e:
                    pass

            siemplify.LOGGER.info(f"Finished processing entity: {entity.identifier}")

        # Request for linking the objects
        for key, value in objects_to_link.items():
            link_obj = threatq_manager.link_entities(
                object_type1=source_object_type,
                object_type2=value,
                object_id1=source_object_id,
                object_id2=key,
            )
            obj_identifier = threatq_manager.get_value_param(
                object_type=value, link_obj=link_obj
            )
            if obj_identifier and obj_identifier not in successful_entities:
                json_results[obj_identifier] = link_obj.to_json()
                successful_entities.append(obj_identifier)

        if successful_entities:
            output_message += (
                "Successfully linked the following entities to object '{}' with value '{}' in "
                "ThreatQ: \n{}".format(
                    object_type,
                    object_identifier,
                    "\n".join([entity for entity in successful_entities]),
                )
            )
            result_value = True
            siemplify.result.add_result_json(
                convert_dict_to_json_result_dict(json_results)
            )
        else:
            output_message = f"No entities were linked to object '{object_type}' with value '{object_identifier}'"

        # Entities not existing in ThreatQ
        identifiers_list = [entity.identifier for entity in siemplify.target_entities]
        failed_entities = list(set(identifiers_list) - set(successful_entities))

        if failed_entities and successful_entities:
            output_message += (
                "\nAction was not able to link the following entities to object '{}' "
                "with value '{}' in ThreatQ:\n{}".format(
                    object_type,
                    object_identifier,
                    "\n".join([entity for entity in failed_entities]),
                )
            )

    except ObjectNotFoundException as e:
        output_message = f"{object_type} object with value {object_identifier} was not found in ThreatQ."
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)

    except Exception as e:
        output_message = (
            f'Error executing action "Link Entities To Object". Reason: {e}'
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
