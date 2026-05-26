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
from enum import Enum
from typing import Any

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from TIPCommon.types import SingleJson


class ExecutionScope(Enum):
    ExecutionScopeUnspecified = 0
    Alert = 1
    Case = 2


def get_fields_to_enrich(fields: list[str], event_properties: SingleJson) -> SingleJson:
    """Extract requested fields from event properties.

    Args:
        fields: List of fields to extract.
        event_properties: The event's additional properties.

    Returns:
        A dictionary of fields and their values.
    """
    lower_dict: SingleJson = {k.lower(): v for k, v in event_properties.items()}
    return {
        field.lower(): lower_dict[field.lower()]
        for field in fields
        if field.lower() in lower_dict
    }


def get_alert_entities(
    siemplify: SiemplifyAction,
    alert: Any,
    execution_scope: Any,
) -> list[Any]:
    """Retrieve entities associated with the given alert based on execution scope.

    Args:
        siemplify: The Siemplify action instance.
        alert: The alert to process.
        execution_scope: The current execution scope.

    Returns:
        A list of entities associated with the alert.
    """
    if execution_scope.value == ExecutionScope.Alert.value:
        return siemplify.target_entities
    return [
        e for e in siemplify.target_entities if e.alert_identifier == alert.identifier
    ]


def process_alert(
    siemplify: SiemplifyAction,
    alert: Any,
    fields: list[str],
    execution_scope: Any,
) -> tuple[list[Any], SingleJson]:
    """Process a single alert to enrich its entities.

    Args:
        siemplify: The Siemplify action instance.
        alert: The alert to process.
        fields: The fields to extract and enrich.
        execution_scope: The current execution scope.

    Returns:
        A tuple of updated entities and a dictionary of enriched fields.
    """
    updated_entities: list[Any] = []
    fields_to_enrich: SingleJson = {}

    event: Any = next(iter(getattr(alert, "security_events", [])), None)
    if event:
        extracted_fields: SingleJson = get_fields_to_enrich(
            fields, event.additional_properties
        )
        if extracted_fields:
            alert_entities: list[Any] = get_alert_entities(
                siemplify, alert, execution_scope
            )
            if alert_entities:
                fields_to_enrich = extracted_fields
                for entity in alert_entities:
                    entity.additional_properties.update(fields_to_enrich)
                    updated_entities.append(entity)
                    siemplify.result.add_json(
                        entity.identifier,
                        json.dumps(fields_to_enrich),
                    )

    return updated_entities, fields_to_enrich


@output_handler
def main() -> None:
    siemplify: SiemplifyAction = SiemplifyAction()

    execution_scope: Any = getattr(
        siemplify,
        "execution_scope",
        ExecutionScope.Alert,
    )

    siemplify.LOGGER.info(f"Running in {execution_scope.name.lower()} scope")

    if execution_scope.value == ExecutionScope.Alert.value:
        target_alerts: list[Any] = [siemplify.current_alert]
    else:
        target_alerts: list[Any] = getattr(siemplify.case, "open_alerts", siemplify.case.alerts)

    fields: list[str] = siemplify.parameters.get("Fields to enrich").split(",")
    updated_entities: list[Any] = []
    all_fields_to_enrich: SingleJson = {}

    for alert in target_alerts:
        try:
            updated, enriched_fields = process_alert(
                siemplify, alert, fields, execution_scope
            )
            updated_entities.extend(updated)
            if execution_scope.value == ExecutionScope.Case.value:
                all_fields_to_enrich[alert.identifier] = enriched_fields
            else:
                all_fields_to_enrich.update(enriched_fields)
        except Exception as e:
            siemplify.LOGGER.error(
                "Failed to process alert "
                f"{getattr(alert, 'identifier', alert)}: {e}"
            )

    count_updated_entities: int = len(updated_entities)

    if count_updated_entities > 0:
        siemplify.update_entities(updated_entities)

    if execution_scope.value == ExecutionScope.Alert.value:
        output_message = (
            f"{count_updated_entities} entities were successfully enriched"
        )
    else:
        output_message = (
            f"{count_updated_entities} entities were successfully enriched "
            "for all case open alerts"
        )

    siemplify.result.add_result_json(json.dumps(all_fields_to_enrich))
    siemplify.end(
        output_message,
        count_updated_entities,
        EXECUTION_STATE_COMPLETED,
    )


if __name__ == "__main__":
    main()
