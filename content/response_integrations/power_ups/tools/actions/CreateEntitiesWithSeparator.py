# Copyright 2025 Google LLC
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

import ipaddress
import json

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import add_prefix_to_dict, output_handler


def check_if_entity_exists(target_entities, entity_identifier):
    """Verify if entity with such identifier already exists within the case.

    :param target_entities: enumeration of case entities (e.g. siemplify.target_entities)
    :param entity_identifier: identifier of entity, which we're checking
    :return: True if entity with such identier exists already within case; False - otherwise
    """
    for entity in target_entities:
        if entity.identifier.strip() == entity_identifier:
            return True
    return False


def get_alert_entities(siemplify):
    return [entity for alert in siemplify.case.alerts for entity in alert.entities]


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = "Create Entities"
    siemplify.LOGGER.info("-----------Action started--------------")
    entities_identifiers = siemplify.parameters["Entities Identifiers"]
    entity_type = siemplify.parameters["Entity Type"]
    json_data = siemplify.parameters.get("Enrichment JSON", None)
    if json_data == "// Enter some code here":
        json_data = None
    enrichment_json = {}
    properties = enrichment_json.copy()
    # print(json_data)
    if json_data:
        enrichment_json = json.loads(json_data)
        enrichment_prefix = siemplify.parameters.get("PrefixForEnrichment", None)
        if enrichment_prefix:
            properties = add_prefix_to_dict(enrichment_json, enrichment_prefix)
        else:
            properties = enrichment_json.copy()
    is_internal = siemplify.parameters.get("Is Internal", "false").lower() == "true"
    is_suspicious = siemplify.parameters.get("Is Suspicious", "false").lower() == "true"
    is_enriched = True
    is_vulnerable = False
    result_value = "true"
    status = EXECUTION_STATE_COMPLETED

    separator = siemplify.parameters.get("Entities Separator", ",") or ","
    siemplify.LOGGER.info(f"Splitting entities by {separator}")
    entities_identifiers_list = entities_identifiers.split(separator)
    alert_entities = get_alert_entities(siemplify)
    error_messages = []
    warning_messages = []
    entities_to_enrich = []
    success_entities = []
    updated_entities = []
    json_result = {}
    json_result["created"] = []
    json_result["enriched"] = []
    json_result["failed"] = []
    output_message = ""
    for entity_identifier in entities_identifiers_list:
        entity_identifier = str(entity_identifier.strip()).upper()
        if entity_identifier:
            try:
                if check_if_entity_exists(alert_entities, entity_identifier):
                    # if json_data:
                    #    entities_to_enrich.append(entity_identifier)
                    json_result["failed"].append(entity_identifier)
                else:
                    properties["is_new_entity"] = True
                    if entity_type == "ADDRESS":
                        try:
                            test_ip = ipaddress.ip_address(entity_identifier)
                            siemplify.add_entity_to_case(
                                entity_identifier,
                                entity_type,
                                is_internal,
                                is_suspicious,
                                is_enriched,
                                is_vulnerable,
                                properties,
                            )
                            success_entities.append(entity_identifier)
                            json_result["created"].append(entity_identifier)
                            if len(properties) > 1:
                                json_result["enriched"].append(entity_identifier)
                        except Exception as e:
                            message = f"Entity {entity_identifier} Creation failed. Not a valid IP Address: {e}"
                            siemplify.LOGGER.error(message)
                            error_messages.append(message)
                    else:
                        siemplify.add_entity_to_case(
                            entity_identifier,
                            entity_type,
                            is_internal,
                            is_suspicious,
                            is_enriched,
                            is_vulnerable,
                            properties,
                        )

                        success_entities.append(entity_identifier)
                        json_result["created"].append(entity_identifier)
                        if len(properties) > 1:
                            json_result["enriched"].append(entity_identifier)

            except Exception as e:
                error_message = (
                    f"Entity {entity_identifier} Creation failed. error: {e}"
                )
                siemplify.LOGGER.error(error_message)
                siemplify.LOGGER.exception(e)
                error_messages.append(error_message)
                json_result["failed"].append(entity_identifier)

    if entities_to_enrich:
        for entity in alert_entities:
            for enrich_entity in entities_to_enrich:
                if enrich_entity.upper() == entity.identifier.upper():
                    entity.additional_properties.update(properties)
                    updated_entities.append(entity)
                    output_message += f"Entity {entity.identifier} Already Exists, but enrichment still added.\n"
                    json_result["enriched"].append(entity.identifier)
        siemplify.update_entities(updated_entities)

    siemplify.result.add_result_json(json_result)
    if success_entities:
        output_message += f"{','.join(success_entities)} created successfully."
    else:
        output_message += "No entities were created."

    if warning_messages:
        output_message += "{0} \n WARNINGS: \n {1}".format(
            output_message,
            "\n".join(warning_messages),
        )

    if error_messages:
        output_message = "{0} \n ERRORS: \n {1}".format(
            output_message,
            "\n".join(error_messages),
        )
        status = EXECUTION_STATE_FAILED
        result_value = "false"

    siemplify.LOGGER.info("-----------Action done--------------")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
