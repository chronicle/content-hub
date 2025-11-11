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

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from TIPCommon.rest.soar_api import get_investigator_data
from TIPCommon.types import SingleJson

ACTION_NAME = "Enrich Source and Destinations"


def get_alert_entities(siemplify):
    return [
        entity
        for alert in siemplify.case.alerts
        for entity in alert.entities
        if alert.identifier == siemplify.current_alert.identifier
    ]


def get_ip_entities(siemplify):
    return [
        entity.identifier
        for entity in get_alert_entities(siemplify)
        if entity.entity_type == "ADDRESS"
    ]


def get_host_entities(siemplify):
    return [
        entity.identifier
        for entity in get_alert_entities(siemplify)
        if entity.entity_type == "HOSTNAME"
    ]


def get_current_alert(alerts, current_alert):
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
    target_lists = {
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
        key_map = {"source": "sources", "destination": "destinations"}
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


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = ACTION_NAME
    investigator_res = get_investigator_data(
        chronicle_soar=siemplify,
        case_id=siemplify.case_id,
        alert_identifier=siemplify.current_alert.identifier,
    )
    alert = None
    if "alerts" in investigator_res:
        alert = get_current_alert(
            investigator_res["alerts"],
            siemplify.current_alert.identifier,
        )
    else:
        alert = investigator_res
    (sources, dests) = get_sources_and_dest(alert)
    updated_entities = []

    for source in sources:
        for entity in get_alert_entities(siemplify):
            if entity.identifier.casefold() == source.casefold():
                entity.additional_properties.update({"isSource": "true"})
                updated_entities.append(entity)
                break
    for dest in dests:
        for entity in get_alert_entities(siemplify):
            if entity.identifier.casefold() == dest.casefold():
                entity.additional_properties.update({"isDest": "true"})
                updated_entities.append(entity)
                break

    siemplify.update_entities(updated_entities)
    status = EXECUTION_STATE_COMPLETED
    output_message = "output message : Enrichment added."
    result_value = None

    siemplify.LOGGER.info(
        f"\n  status: {status}\n  result_value: {result_value}\n"
        f"output_message: {output_message}",
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
