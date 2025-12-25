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

import json
import re
import time

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import convert_dict_to_json_result_dict, output_handler
from TIPCommon.data_models import CreateEntity
from TIPCommon.rest.soar_api import create_entity

ACTION_NAME = "Create Entity Relationships"


def get_alert_entities(siemplify):
    alert_entities = []
    for alert in siemplify.case.alerts:
        for entity in alert.entities:
            if entity.alert_identifier == siemplify.current_alert.identifier:
                alert_entities.append(entity)
    return alert_entities


def create_entity_relationship_by_type(
    siemplify,
    new_entity,
    entity_type,
    json_payload,
):
    payload = json_payload.copy()
    payload["typesToConnect"].append(entity_type)
    payload["entityIdentifier"] = new_entity
    entity_to_create = CreateEntity(
        case_id=payload["caseId"],
        alert_identifier=payload["alertIdentifier"],
        entity_type=payload["entityType"],
        entity_identifier=new_entity,
        entity_to_connect_regex=None,
        types_to_connect=payload["typesToConnect"].append(entity_type),
        is_primary_link=payload["isPrimaryLink"],
        is_directional=payload["isDirectional"],
    )
    create_entity(siemplify, entity_to_create)


def create_entity_relationship_by_entity(
    siemplify,
    new_entity,
    linked_entity,
    json_payload,
):
    payload = json_payload.copy()
    payload["entityToConnectRegEx"] = f"{re.escape(linked_entity)}$"
    payload["entityIdentifier"] = new_entity
    entity_to_create = CreateEntity(
        case_id=payload["caseId"],
        alert_identifier=payload["alertIdentifier"],
        entity_type=payload["entityType"],
        entity_identifier=new_entity,
        entity_to_connect_regex=f"{re.escape(linked_entity)}$",
        types_to_connect=[],
        is_primary_link=payload["isPrimaryLink"],
        is_directional=payload["isDirectional"],
    )
    create_entity(siemplify, entity_to_create)


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = ACTION_NAME
    output_message = "No Entity was created"
    result_value = "False"
    status = EXECUTION_STATE_COMPLETED
    separator = siemplify.extract_action_param("Separator Character", ",")
    entity_identifiers = list(
        filter(
            None,
            [
                x.strip()
                for x in siemplify.extract_action_param(
                    "Entity Identifier(s)",
                    " ",
                ).split(separator)
            ],
        ),
    )
    linked_entities = list(
        filter(
            None,
            [
                x.strip()
                for x in siemplify.extract_action_param(
                    "Target Entity Identifier(s)",
                    " ",
                ).split(separator)
            ],
        ),
    )
    linked_entity_type = siemplify.extract_action_param("Target Entity Type", None)

    entity_type = siemplify.extract_action_param("Entity Identifier(s) Type")
    is_relation_type = False
    is_source = False
    rel_direction = siemplify.extract_action_param("Connect As")

    json_data = siemplify.parameters.get("Enrichment JSON", None)
    if json_data == "// Enter some code here":
        json_data = None
    enrichment_json = {}

    if json_data:
        enrichment_json = json.loads(json_data)

    if rel_direction == "Source":
        is_source = True
        is_relation_type = True

    if rel_direction == "Destination":
        is_source = False
        is_relation_type = True

    if rel_direction == "Linked":
        is_relation_type = False

    updated_entities = []

    json_results = {}
    case_id = siemplify.case_id
    alert_identifier = siemplify.current_alert.identifier
    output_message = ""

    json_payload = {
        "caseId": case_id,
        "alertIdentifier": alert_identifier,
        "entityType": entity_type,
        "isPrimaryLink": is_relation_type,
        "isDirectional": is_source,
        "typesToConnect": [],
    }

    target_entities = []

    for entity in entity_identifiers:
        json_results[entity] = {}

    siemplify.LOGGER.info(f"Entities to create:{entity_identifiers}")
    alert_entities = get_alert_entities(siemplify)

    for entity in alert_entities:
        if len(linked_entities) > 0:
            for l_entity in linked_entities:
                if (
                    entity.entity_type == linked_entity_type
                    and entity.identifier.casefold() == l_entity.casefold()
                ):
                    target_entities.append(entity.identifier)
        elif entity.entity_type == linked_entity_type:
            target_entities.append(entity.identifier)

    siemplify.LOGGER.info(f"Possible Relationship entities:{target_entities}")

    if len(target_entities) == 0:
        output_message = "No entity relationships found. Did not create entity."

    if len(target_entities) == len(entity_identifiers) and len(linked_entities) > 0:
        for linked_entity, new_entity_identifier in zip(
            target_entities,
            entity_identifiers,
            strict=False,
        ):
            linked_entities_arr = []
            try:
                create_entity_relationship_by_entity(
                    siemplify,
                    new_entity_identifier,
                    linked_entity,
                    json_payload,
                )
                result_value = True
                linked_entities_arr.append(linked_entity)
                output_message += (
                    f"The Entity {new_entity_identifier} was created and linked to {linked_entity}"
                    f" : {linked_entity_type} successfully\n"
                )
            except Exception as e:
                siemplify.LOGGER.error(
                    f"Error creating entity:{linked_entity}, error: {e}",
                )
                status = EXECUTION_STATE_FAILED

            siemplify.LOGGER.info(
                f"The Entity {new_entity_identifier} was created and linked to {linked_entity}"
                f" : {linked_entity_type} successfully\n",
            )

            json_results[new_entity_identifier]["status"] = "created"
            linked_entity_obj = {}
            linked_entity_obj["entity_type"] = linked_entity_type
            linked_entity_obj["entities"] = linked_entities_arr

            json_results[new_entity_identifier]["linked_entities"] = linked_entity_obj
            json_results[new_entity_identifier]["entity_type"] = entity_type

    elif (
        len(target_entities) > len(entity_identifiers)
        and len(entity_identifiers) == 1
        and len(linked_entities) > 0
    ):
        linked_entities_arr = []
        for target_entity in target_entities:
            try:
                create_entity_relationship_by_entity(
                    siemplify,
                    entity_identifiers[0],
                    target_entity,
                    json_payload,
                )
                result_value = True
                linked_entities_arr.append(target_entity)
            except Exception as e:
                siemplify.LOGGER.error(
                    f"Error creating entity:{target_entity}, error: {e}",
                )
                status = EXECUTION_STATE_FAILED
            output_message += (
                f"The Entity {entity_identifiers[0]} was created and linked to {target_entity}"
                f" : {linked_entity_type} successfully\n"
            )

            siemplify.LOGGER.info(
                f"The Entity {entity_identifiers[0]} was created and linked to {target_entity} "
                f": {linked_entity_type} successfully\n",
            )

        json_results[entity_identifiers[0]]["status"] = "created"
        linked_entity_obj = {}
        linked_entity_obj["entity_type"] = linked_entity_type
        linked_entity_obj["entities"] = linked_entities_arr
        json_results[entity_identifiers[0]]["linked_entities"] = linked_entity_obj

    elif (
        len(entity_identifiers) > len(target_entities)
        and len(target_entities) == 1
        and len(linked_entities) > 0
    ):
        for new_entity_identifier in entity_identifiers:
            linked_entities_arr = []
            linked_entity = target_entities[0]
            try:
                create_entity_relationship_by_entity(
                    siemplify,
                    new_entity_identifier,
                    linked_entity,
                    json_payload,
                )
                result_value = True
                linked_entities_arr.append(linked_entity)
            except Exception as e:
                siemplify.LOGGER.error(
                    f"Error creating entity:{linked_entity}, error: {e}",
                )
                status = EXECUTION_STATE_FAILED
            output_message += (
                f"The Entity {new_entity_identifier} was created and linked to {linked_entity}"
                f" : {linked_entity_type} successfully\n"
            )

            siemplify.LOGGER.info(
                f"The Entity {new_entity_identifier} was created and linked to {linked_entity}"
                f" : {linked_entity_type} successfully\n",
            )

            json_results[new_entity_identifier]["status"] = "created"
            linked_entity_obj = {}
            linked_entity_obj["entity_type"] = linked_entity_type
            linked_entity_obj["entities"] = linked_entities_arr
            json_results[new_entity_identifier]["linked_entities"] = linked_entity_obj
            json_results[new_entity_identifier]["entity_type"] = entity_type

    elif not linked_entities and len(target_entities) != 0:
        linked_entities_arr = target_entities
        for new_entity_identifier in entity_identifiers:
            try:
                create_entity_relationship_by_type(
                    siemplify,
                    new_entity_identifier,
                    linked_entity_type,
                    json_payload,
                )
            except Exception as e:
                siemplify.LOGGER.error(
                    f"Error creating entity:{new_entity_identifier}, error: {e}",
                )
                status = EXECUTION_STATE_FAILED
            result_value = True
            target_entities_str = ",".join(target_entities)
            siemplify.LOGGER.info(
                f"The Entity {new_entity_identifier} was created and linked to "
                f"{target_entities_str} successfully\n",
            )
            output_message += (
                f"The Entity {new_entity_identifier} was created and linked to "
                f"{target_entities_str} successfully\n"
            )
            json_results[new_entity_identifier]["status"] = "created"

            linked_entity_obj = {}
            linked_entity_obj["entity_type"] = linked_entity_type
            linked_entity_obj["entities"] = linked_entities_arr
            json_results[new_entity_identifier]["linked_entities"] = linked_entity_obj
            json_results[new_entity_identifier]["entity_type"] = entity_type

    time.sleep(3)
    siemplify.load_case_data()
    if enrichment_json:
        alert_entities = get_alert_entities(siemplify)
        for new_entity in json_results:
            for entity in alert_entities:
                if new_entity.strip() == entity.identifier.strip():
                    entity.additional_properties.update(enrichment_json)
                    updated_entities.append(entity)
                    output_message += (
                        f"Enrichment added for entity: {entity.identifier}.\n"
                    )
                    break
        siemplify.update_entities(updated_entities)
    siemplify.result.add_result_json(convert_dict_to_json_result_dict(json_results))
    siemplify.result.add_json("Json", json_results)

    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
