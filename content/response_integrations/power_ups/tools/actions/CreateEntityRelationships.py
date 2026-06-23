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
from typing import TYPE_CHECKING

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyUtils import convert_dict_to_json_result_dict
from TIPCommon.base.action import Action
from TIPCommon.data_models import CreateEntity
from TIPCommon.extraction import extract_action_param
from TIPCommon.rest.soar_api import create_entity
from TIPCommon.transformation import string_to_multi_value
from TIPCommon.types import SingleJson

from ..core.ToolsCommon import ExecutionScope, get_case_alerts

if TYPE_CHECKING:
    from typing import Never

ACTION_NAME: str = "Create Entity Relationships"


class CreateEntityRelationshipsAction(Action):
    def __init__(self) -> None:
        super().__init__(ACTION_NAME)

    def _extract_action_parameters(self) -> None:
        separator = extract_action_param(
            self.soar_action,
            param_name="Separator Character",
            default_value=",",
            is_mandatory=False,
            print_value=True,
        )
        self.params.separator = separator
        
        entity_identifiers_raw = extract_action_param(
            self.soar_action,
            param_name="Entity Identifier(s)",
            default_value=" ",
            is_mandatory=False,
            print_value=True,
        )
        self.params.entity_identifiers = [
            x.strip()
            for x in string_to_multi_value(
                entity_identifiers_raw, delimiter=separator
            )
        ]
        
        linked_entities_raw = extract_action_param(
            self.soar_action,
            param_name="Target Entity Identifier(s)",
            default_value=" ",
            is_mandatory=False,
            print_value=True,
        )
        self.params.linked_entities = [
            x.strip()
            for x in string_to_multi_value(
                linked_entities_raw, delimiter=separator
            )
        ]
        
        self.params.linked_entity_type = extract_action_param(
            self.soar_action,
            param_name="Target Entity Type",
            is_mandatory=False,
            print_value=True,
        )
        self.params.entity_type = extract_action_param(
            self.soar_action,
            param_name="Entity Identifier(s) Type",
            is_mandatory=True,
            print_value=True,
        )
        self.params.rel_direction = extract_action_param(
            self.soar_action,
            param_name="Connect As",
            is_mandatory=True,
            print_value=True,
        )
        self.params.json_data = self.soar_action.parameters.get("Enrichment JSON", None)

    def _validate_params(self) -> None:
        pass

    def _init_api_clients(self) -> None:
        """Initialize API clients if required (placeholder)."""

    def _perform_action(self, __: Never) -> None:
        json_results: SingleJson = {}
        for entity in self.params.entity_identifiers:
            json_results[entity] = {}

        is_relation_type, is_source = self._initialize_payload_flags()
        target_alerts = self._get_target_alerts()
            
        enrichment_json: SingleJson = {}
        if self.params.json_data and self.params.json_data != "// Enter some code here":
            enrichment_json = json.loads(self.params.json_data)
            
        status: int = EXECUTION_STATE_COMPLETED
        result_value: bool | str = "False"
        
        for alert in target_alerts:
            status, result_value = self._process_alert(
                alert,
                is_relation_type,
                is_source,
                json_results,
                status,
                result_value,
            )

        time.sleep(3)
        self.soar_action.load_case_data()
        
        if enrichment_json:
            self._apply_enrichment(target_alerts, json_results, enrichment_json)
            
        result_dict: SingleJson = convert_dict_to_json_result_dict(json_results)
        self.soar_action.result.add_result_json(result_dict)
        self.soar_action.result.add_json("Json", json_results)
        
        self.soar_action.end(self.output_message, result_value, status)

    def _initialize_payload_flags(self) -> tuple[bool, bool]:
        is_relation_type: bool = False
        is_source: bool = False
        
        if self.params.rel_direction == "Source":
            is_source = True
            is_relation_type = True
        elif self.params.rel_direction == "Destination":
            is_source = False
            is_relation_type = True
        elif self.params.rel_direction == "Linked":
            is_relation_type = False
            
        return is_relation_type, is_source

    def _get_target_alerts(self) -> list:
        execution_scope = getattr(
            self.soar_action, "execution_scope", ExecutionScope.Alert
        )
        if execution_scope.value == ExecutionScope.Alert.value:
            self.output_message = "No Entity was created"
            return [self.soar_action.current_alert]
        
        self.output_message = ""
        return get_case_alerts(self.soar_action)

    def _process_alert(
        self,
        alert,
        is_relation_type: bool,
        is_source: bool,
        json_results: SingleJson,
        status: int,
        result_value: bool | str,
    ) -> tuple[int, bool | str]:
        case_id: str = self.soar_action.case_id
        alert_identifier: str = alert.identifier
        
        json_payload: SingleJson = {
            "caseId": case_id,
            "alertIdentifier": alert_identifier,
            "entityType": self.params.entity_type,
            "isPrimaryLink": is_relation_type,
            "isDirectional": is_source,
            "typesToConnect": [],
        }
        
        target_entities: list[str] = self._find_target_entities(alert)
        
        self.soar_action.LOGGER.info(
            f"Possible Relationship entities:{target_entities}"
        )

        execution_scope = getattr(
            self.soar_action, "execution_scope", ExecutionScope.Alert
        )

        if len(target_entities) == 0:
            if execution_scope.value == ExecutionScope.Alert.value:
                self.output_message = (
                    "No entity relationships found. Did not create entity."
                )
            else:
                self.output_message += (
                    f"No entity relationships found for alert {alert_identifier}.\n"
                )
            return status, result_value

        return self._create_relationships(
            target_entities,
            json_payload,
            json_results,
            status,
            result_value,
        )

    def _find_target_entities(self, alert) -> list[str]:
        target_entities: list[str] = []
        alert_entities: list = alert.entities
        
        self.soar_action.LOGGER.info(
            f"Entities to create:{self.params.entity_identifiers}"
        )
        
        for entity in alert_entities:
            if len(self.params.linked_entities) > 0:
                for l_entity in self.params.linked_entities:
                    if (
                        entity.entity_type == self.params.linked_entity_type
                        and entity.identifier.casefold() == l_entity.casefold()
                    ):
                        target_entities.append(entity.identifier)
            elif entity.entity_type == self.params.linked_entity_type:
                target_entities.append(entity.identifier)
                
        return target_entities

    def _create_relationships(
        self,
        target_entities: list[str],
        json_payload: SingleJson,
        json_results: SingleJson,
        status: int,
        result_value: bool | str,
    ) -> tuple[int, bool | str]:
        if (
            len(target_entities) == len(self.params.entity_identifiers)
            and len(self.params.linked_entities) > 0
        ):
            return self._create_one_to_one_relationships(
                target_entities,
                json_payload,
                json_results,
                status,
                result_value,
            )

        elif (
            len(target_entities) > len(self.params.entity_identifiers)
            and len(self.params.entity_identifiers) == 1
            and len(self.params.linked_entities) > 0
        ):
            return self._create_one_to_many_relationships(
                target_entities,
                json_payload,
                json_results,
                status,
                result_value,
            )

        elif (
            len(self.params.entity_identifiers) > len(target_entities)
            and len(target_entities) == 1
            and len(self.params.linked_entities) > 0
        ):
            return self._create_many_to_one_relationships(
                target_entities,
                json_payload,
                json_results,
                status,
                result_value,
            )

        elif not self.params.linked_entities and len(target_entities) != 0:
            return self._create_type_relationships(
                target_entities,
                json_payload,
                json_results,
                status,
                result_value,
            )
            
        return status, result_value

    def _create_and_log_entity_relationship(
        self,
        new_entity_identifier: str,
        linked_entity: str,
        json_payload: SingleJson,
        json_results: SingleJson,
    ) -> bool:
        try:
            self._create_entity_relationship_by_entity(
                new_entity_identifier,
                linked_entity,
                json_payload,
            )
            if self.output_message == "No Entity was created":
                self.output_message = ""
            self.output_message += (
                f"The Entity {new_entity_identifier} was created and linked "
                f"to {linked_entity} : {self.params.linked_entity_type} "
                f"successfully\n"
            )
            self.soar_action.LOGGER.info(
                f"The Entity {new_entity_identifier} was created and linked "
                f"to {linked_entity} : {self.params.linked_entity_type} "
                f"successfully\n",
            )
            self._update_json_results(
                json_results, new_entity_identifier, linked_entity
            )
            return True
        except Exception as e:
            self.soar_action.LOGGER.error(
                f"Error creating entity:{linked_entity}, error: {e}",
            )
            return False

    def _update_json_results(
        self,
        json_results: SingleJson,
        new_entity_identifier: str,
        linked_entity: str,
    ) -> None:
        json_results[new_entity_identifier]["status"] = "created"
        linked_entity_obj = json_results[new_entity_identifier].get(
            "linked_entities", {}
        )
        if not linked_entity_obj:
            linked_entity_obj["entity_type"] = self.params.linked_entity_type
            linked_entity_obj["entities"] = []
            json_results[new_entity_identifier]["linked_entities"] = linked_entity_obj
            json_results[new_entity_identifier]["entity_type"] = self.params.entity_type
            
        linked_entity_obj["entities"].append(linked_entity)

    def _create_one_to_one_relationships(
        self,
        target_entities: list[str],
        json_payload: SingleJson,
        json_results: SingleJson,
        status: int,
        result_value: bool | str,
    ) -> tuple[int, bool | str]:
        for linked_entity, new_entity_identifier in zip(
            target_entities,
            self.params.entity_identifiers,
            strict=False,
        ):
            success = self._create_and_log_entity_relationship(
                new_entity_identifier,
                linked_entity,
                json_payload,
                json_results,
            )
            if success:
                result_value = True
            else:
                status = EXECUTION_STATE_FAILED
                
        return status, result_value

    def _create_one_to_many_relationships(
        self,
        target_entities: list[str],
        json_payload: SingleJson,
        json_results: SingleJson,
        status: int,
        result_value: bool | str,
    ) -> tuple[int, bool | str]:
        new_entity_identifier = self.params.entity_identifiers[0]
        for target_entity in target_entities:
            success = self._create_and_log_entity_relationship(
                new_entity_identifier,
                target_entity,
                json_payload,
                json_results,
            )
            if success:
                result_value = True
            else:
                status = EXECUTION_STATE_FAILED
                
        return status, result_value

    def _create_many_to_one_relationships(
        self,
        target_entities: list[str],
        json_payload: SingleJson,
        json_results: SingleJson,
        status: int,
        result_value: bool | str,
    ) -> tuple[int, bool | str]:
        linked_entity = target_entities[0]
        for new_entity_identifier in self.params.entity_identifiers:
            success = self._create_and_log_entity_relationship(
                new_entity_identifier,
                linked_entity,
                json_payload,
                json_results,
            )
            if success:
                result_value = True
            else:
                status = EXECUTION_STATE_FAILED
                
        return status, result_value

    def _create_type_relationships(
        self,
        target_entities: list[str],
        json_payload: SingleJson,
        json_results: SingleJson,
        status: int,
        result_value: bool | str,
    ) -> tuple[int, bool | str]:
        for new_entity_identifier in self.params.entity_identifiers:
            try:
                self._create_entity_relationship_by_type(
                    new_entity_identifier,
                    self.params.linked_entity_type,
                    json_payload,
                )
                result_value = True
                if self.output_message == "No Entity was created":
                    self.output_message = ""
                target_entities_str = ",".join(target_entities)
                self.soar_action.LOGGER.info(
                    f"The Entity {new_entity_identifier} was created and linked to "
                    f"{target_entities_str} successfully\n",
                )
                self.output_message += (
                    f"The Entity {new_entity_identifier} was created and "
                    f"linked to {target_entities_str} successfully\n"
                )
                
                json_results[new_entity_identifier]["status"] = "created"
                linked_entity_obj = {}
                linked_entity_obj["entity_type"] = self.params.linked_entity_type
                linked_entity_obj["entities"] = target_entities
                json_results[new_entity_identifier][
                    "linked_entities"
                ] = linked_entity_obj
                json_results[new_entity_identifier][
                    "entity_type"
                ] = self.params.entity_type
                
            except Exception as e:
                self.soar_action.LOGGER.error(
                    f"Error creating entity:{new_entity_identifier}, error: {e}",
                )
                status = EXECUTION_STATE_FAILED
                
        return status, result_value

    def _apply_enrichment(
        self,
        target_alerts: list,
        json_results: SingleJson,
        enrichment_json: SingleJson,
    ) -> None:
        updated_entities: list = []
        new_entities_set = {k.strip() for k in json_results.keys()}
        
        for alert in target_alerts:
            for entity in alert.entities:
                if entity.identifier.strip() in new_entities_set:
                    entity.additional_properties.update(enrichment_json)
                    updated_entities.append(entity)
                    self.output_message += (
                        f"Enrichment added for entity: {entity.identifier}.\n"
                    )
        self.soar_action.update_entities(updated_entities)

    def _create_entity_relationship_by_type(
        self,
        new_entity: str,
        entity_type: str,
        json_payload: SingleJson,
    ) -> None:
        payload = dict(json_payload)
        payload["typesToConnect"] = payload.get("typesToConnect", []) + [entity_type]
        payload["entityIdentifier"] = new_entity
        entity_to_create: CreateEntity = CreateEntity(
            case_id=payload["caseId"],
            alert_identifier=payload["alertIdentifier"],
            entity_type=payload["entityType"],
            entity_identifier=new_entity,
            entity_to_connect_regex=None,
            types_to_connect=payload["typesToConnect"],
            is_primary_link=payload["isPrimaryLink"],
            is_directional=payload["isDirectional"],
        )
        create_entity(self.soar_action, entity_to_create)

    def _create_entity_relationship_by_entity(
        self,
        new_entity: str,
        linked_entity: str,
        json_payload: SingleJson,
    ) -> None:
        payload = dict(json_payload)
        payload["entityToConnectRegEx"] = f"{re.escape(linked_entity)}$"
        payload["entityIdentifier"] = new_entity
        entity_to_create: CreateEntity = CreateEntity(
            case_id=payload["caseId"],
            alert_identifier=payload["alertIdentifier"],
            entity_type=payload["entityType"],
            entity_identifier=new_entity,
            entity_to_connect_regex=f"{re.escape(linked_entity)}$",
            types_to_connect=[],
            is_primary_link=payload["isPrimaryLink"],
            is_directional=payload["isDirectional"],
        )
        create_entity(self.soar_action, entity_to_create)


def main() -> None:
    CreateEntityRelationshipsAction().run()


if __name__ == "__main__":
    main()
