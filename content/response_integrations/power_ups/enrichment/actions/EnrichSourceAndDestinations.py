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

from enum import Enum
from typing import Any

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from TIPCommon.data_models import Entity
from TIPCommon.rest.soar_api import get_investigator_data
from TIPCommon.types import SingleJson

ACTION_NAME: str = "Enrich Source and Destinations"


class ExecutionScope(Enum):
    ExecutionScopeUnspecified = 0
    Alert = 1
    Case = 2


def get_alert_entities(
    siemplify: SiemplifyAction,
    alert_identifier: str,
    execution_scope: Any,
) -> list[Entity]:
    """Retrieve entities associated with a specific alert.

    Args:
        siemplify: The Siemplify action instance.
        alert_identifier: The identifier of the alert.
        execution_scope: The current execution scope.

    Returns:
        A list of entities associated with the alert.
    """
    if execution_scope.value == ExecutionScope.Alert.value:
        return siemplify.target_entities
    return [
        e for e in siemplify.target_entities if e.alert_identifier == alert_identifier
    ]


def get_current_alert(
    alerts: list[SingleJson],
    current_alert: str,
) -> SingleJson | None:
    """Retrieve the alert data matching the current alert identifier from the list.

    Args:
        alerts: The list of alerts to search in.
        current_alert: The specific alert identifier to match.

    Returns:
        The matching alert dictionary if found, else None.
    """
    for alert in alerts:
        if alert["identifier"] == current_alert:
            return alert


def get_sources_and_dest(
    alert: SingleJson | list[SingleJson],
) -> tuple[list[str], list[str]]:
    """Get sources and destinations from alert.

    Args:
        alert (SingleJson | list[SingleJson]): Chronicle alert.

    Returns:
        tuple[list[str], list[str]]: Tuple containing list of sources and destinations.
    """
    target_lists: dict[str, list[str]] = {
        "sources": [],
        "destinations": [],
    }

    if isinstance(alert, dict) and "securityEventCards" in alert:
        for event_card in alert["securityEventCards"]:
            for key in target_lists:
                target_lists[key].extend(event_card.get(key, []))

        for key, lst in target_lists.items():
            if lst and isinstance(lst[0], dict):
                target_lists[key] = [
                    x.get("identifier") for x in lst if isinstance(x, dict)
                ]

    else:
        key_map: dict[str, str] = {"source": "sources", "destination": "destinations"}
        for event_card in alert:
            for group in event_card.get("fields", []):
                group_name = group.get("groupName", "").lower()
                mapped_key = key_map.get(group_name)
                if not mapped_key:
                    continue

                for item in group.get("items", []):
                    if value := item.get("value"):
                        target_lists[mapped_key].append(value)

    return target_lists["sources"], target_lists["destinations"]


def get_investigator_alert(
    siemplify: SiemplifyAction,
    target_alert: Any,
) -> SingleJson | None:
    """Retrieve the investigator alert data for a specific alert.

    Args:
        siemplify: The Siemplify action instance.
        target_alert: The alert to retrieve data for.

    Returns:
        The alert data if found, else None.
    """
    investigator_res: SingleJson = get_investigator_data(
        chronicle_soar=siemplify,
        case_id=siemplify.case_id,
        alert_identifier=target_alert.identifier,
    )
    if "alerts" in investigator_res:
        return get_current_alert(
            investigator_res["alerts"],
            target_alert.identifier,
        )
    return investigator_res


def enrich_entities_with_sources_and_dests(
    entities: list[Entity],
    sources: list[str],
    dests: list[str],
) -> list[Entity]:
    """Enrich entities with source and destination properties based on matches.

    Args:
        entities: List of entities to process.
        sources: List of source identifiers.
        dests: List of destination identifiers.

    Returns:
        A list of updated entities.
    """
    source_set = {s.casefold() for s in sources}
    dest_set = {d.casefold() for d in dests}
    updated_entities_map: dict[str, Entity] = {}

    for entity in entities:
        ident = entity.identifier.casefold()
        if ident in source_set:
            entity.additional_properties.update({"isSource": "true"})
            updated_entities_map[entity.identifier] = entity

        if ident in dest_set:
            entity.additional_properties.update({"isDest": "true"})
            updated_entities_map[entity.identifier] = entity

    return list(updated_entities_map.values())


def process_alert(
    siemplify: SiemplifyAction,
    target_alert: Any,
    execution_scope: Any,
) -> list[Entity]:
    """Process a single alert to enrich its source and destination entities.

    Args:
        siemplify: The Siemplify action instance.
        target_alert: The alert to process.
        execution_scope: The current execution scope.

    Returns:
        A list of updated entities.
    """
    updated_entities: list[Entity] = []
    alert_data: SingleJson | None = get_investigator_alert(siemplify, target_alert)

    if alert_data:
        extracted_tuples = get_sources_and_dest(alert_data)
        sources: list[str] = extracted_tuples[0]
        dests: list[str] = extracted_tuples[1]
        if sources or dests:
            current_alert_entities: list[Entity] = get_alert_entities(
                siemplify,
                target_alert.identifier,
                execution_scope,
            )
            if current_alert_entities:
                updated_entities = enrich_entities_with_sources_and_dests(
                    current_alert_entities,
                    sources,
                    dests,
                )

    return updated_entities


@output_handler
def main() -> None:
    siemplify: SiemplifyAction = SiemplifyAction()
    siemplify.script_name = ACTION_NAME

    execution_scope: Any = getattr(
        siemplify,
        "execution_scope",
        ExecutionScope.Alert,
    )

    if execution_scope.value == ExecutionScope.Alert.value:
        target_alerts: list[Any] = [siemplify.current_alert]
    else:
        target_alerts: list[Any] = getattr(siemplify.case, "alerts", [])

    updated_entities: list[Entity] = []

    for target_alert in target_alerts:
        updated: list[Entity] = process_alert(siemplify, target_alert, execution_scope)
        updated_entities.extend(updated)

    siemplify.update_entities(updated_entities)
    status: int = EXECUTION_STATE_COMPLETED
    output_message: str = "output message : Enrichment added."
    result_value: str | None = None

    siemplify.LOGGER.info(
        f"\n  status: {status}\n  result_value: {result_value}\n"
        f"output_message: {output_message}",
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
