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

import json
from typing import Any

from dateutil.parser import parse

from .datamodels import AlertEntity, IncidentAlert
from .exceptions import TimeoutIsApproachingError
from TIPCommon.smp_io import read_content, write_content
from TIPCommon.smp_time import is_approaching_timeout
from TIPCommon.consts import TIMEOUT_THRESHOLD
from TIPCommon.transformation import dict_to_flat
from . import constants
from .utils import find_fallback_value

BACKLOG_IDS_FILE = "backlog_ids.json"
PROCESSED_INCIDENTS_LIST_FILE = "processed_incidents_list.json"
NEXT_PAGE_ALERT_LINK_FILE = "next_page_alert_link.json"

BACKLOG_IDS_DB_KEY = "backlog_ids"
PROCESSED_INCIDENTS_LIST_DB_KEY = "processed_incidents_list"
NEXT_PAGE_ALERT_LINK_DB_KEY = "next_page_alert_link"

IDS_HOURS_LIMIT = 24


class MicrosoftAzureSentinelCommon:
    def __init__(self, siemplify_logger):
        self.siemplify_logger = siemplify_logger

    @staticmethod
    def is_approaching_timeout(
        connector_starting_time: int,
        python_process_timeout: int,
        timeout_threshold: float = TIMEOUT_THRESHOLD,
    ) -> bool:
        """Check if a timeout is approaching.

        Args:
            connector_starting_time: Connector start time
            python_process_timeout: The python process timeout
            timeout_threshold: Timeout threshold

        Returns:
            True if the timeout is approaching, False otherwise
        """
        return is_approaching_timeout(
            connector_starting_time, python_process_timeout, timeout_threshold
        )

    @staticmethod
    def raise_if_timeout(
        connector_starting_time: int,
        python_process_timeout: int,
        timeout_threshold: float = TIMEOUT_THRESHOLD,
    ) -> None:
        """Raise exception if timeout is approaching.

        Args:
            connector_starting_time: Connector start time
            python_process_timeout: The python process timeout
            timeout_threshold: Timeout threshold

        Raises:
            TimeoutIsApproachingError: if the timeout is approaching
        """
        if MicrosoftAzureSentinelCommon.is_approaching_timeout(
            connector_starting_time, python_process_timeout, timeout_threshold
        ):
            raise TimeoutIsApproachingError(
                "Timeout is approaching. Connector will gracefully exit"
            )

    @staticmethod
    def filter_old_ids(alerts, existing_ids):
        """
        Filter ids that were already processed
        :param alerts: {list} The objects to filter
        :param existing_ids: {list} The ids to filter
        :return: {list} The filtered alerts
        """
        new_alerts = []

        for alert in alerts:
            if alert.name not in existing_ids.keys():
                new_alerts.append(alert)

        return new_alerts


def is_date(string, fuzzy=False):
    """
    Return whether the string can be interpreted as a date.

    :param string: str, string to check for date
    :param fuzzy: bool, ignore unknown tokens in string if True
    """
    try:
        parse(string, fuzzy=fuzzy)
        return True

    except ValueError:
        return False


def read_backlog_ids(siemplify):
    """
    Read this specific file content
    :param siemplify: (obj) An instance of the SDK SiemplifyConnectorExecution class.
    :return: the files content
    """
    backlog_ids = read_content(siemplify, BACKLOG_IDS_FILE, BACKLOG_IDS_DB_KEY, {})
    siemplify.LOGGER.info(f"Total alerts in backlog: {len(backlog_ids)}")
    return backlog_ids


def read_next_page_alerts(siemplify):
    """
    Read this specific file content
    :param siemplify: (obj) An instance of the SDK SiemplifyConnectorExecution class.
    :return: the files content
    """
    siemplify.LOGGER.info("Reading next page alerts link.")
    content = read_content(
        siemplify, NEXT_PAGE_ALERT_LINK_FILE, NEXT_PAGE_ALERT_LINK_DB_KEY, ""
    )
    return json.loads(content) if content else None


def read_incidents_numbers(siemplify):
    """
    Read this specific file content
    :param siemplify: (obj) An instance of the SDK SiemplifyConnectorExecution class.
    :return: the files content
    """
    return read_content(
        siemplify, PROCESSED_INCIDENTS_LIST_FILE, PROCESSED_INCIDENTS_LIST_DB_KEY, []
    )


def write_backlog_ids(siemplify, data_to_write):
    """
    Write this specific file content
    :param siemplify: (obj) An instance of the SDK SiemplifyConnectorExecution class
    :param data_to_write: The content to write in the file.
    """
    siemplify.LOGGER.info(f"Total alerts in backlog: {len(data_to_write)}")
    write_content(siemplify, data_to_write, BACKLOG_IDS_FILE, BACKLOG_IDS_DB_KEY, {})


def write_next_page_alerts(siemplify, data_to_write):
    """
    Write this specific file content
    :param siemplify: (obj) An instance of the SDK SiemplifyConnectorExecution class
    :param data_to_write: The content to write in the file.
    """
    siemplify.LOGGER.info(f"Writing next page alerts link - {data_to_write}")

    json_data = json.dumps(data_to_write) if data_to_write else ""
    write_content(
        siemplify, json_data, NEXT_PAGE_ALERT_LINK_FILE, NEXT_PAGE_ALERT_LINK_DB_KEY, ""
    )


def write_incidents_numbers(siemplify, data_to_write):
    """
    Write ids to the ids file
    :param siemplify: (obj) An instance of the SDK SiemplifyConnectorExecution class
    :param data_to_write: The content to write in the file.
    """
    write_content(
        siemplify,
        data_to_write,
        PROCESSED_INCIDENTS_LIST_FILE,
        PROCESSED_INCIDENTS_LIST_DB_KEY,
        [],
    )


def create_regular_alert_events(
    flat_incident: dict[str, str],
    incident_alert: IncidentAlert,
    create_extra_events_for_all_entities: bool,
    product_field_fallback: list[str],
    fallback_logic_debug: bool,
) -> list[dict[str, Any]]:
    """
    Create regular alert events from entities

    Args:
        flat_incident (dict[str, str]): Flattened incident data
        incident_alert (IncidentAlert): IncidentAlert object
        create_extra_events_for_all_entities (bool):
            Specifies if events should be created for all entities
        product_field_fallback (list[str]): List of product field name fallback fields
        fallback_logic_debug (bool): Specifies if fallback logic debug should be enabled

    Returns:
        list[dict]: list of event dicts
    """
    entities = incident_alert.entities or []
    return [
        create_event_from_entity(
            entity,
            incident_alert,
            flat_incident,
            product_field_fallback,
            fallback_logic_debug,
        )
        for entity in entities
        if (
            entity.kind in constants.SUPPORTED_ENTITY_KINDS
            or create_extra_events_for_all_entities
        )
    ]


def create_event_from_entity(
    entity: AlertEntity,
    incident_alert: IncidentAlert,
    flat_incident: dict[str, str],
    product_field_fallback: list[str],
    fallback_logic_debug: bool,
) -> dict[str, Any]:
    """
    Create event from entity

    Args:
        entity (AlertEntity): AlertEntity object
        incident_alert (IncidentAlert): IncidentAlert object
        flat_incident (dict[str, str]): Flattened incident data
        product_field_fallback (list[str]): List of product field name fallback fields
        fallback_logic_debug (bool): Specifies if fallback logic debug should be enabled

    Returns:
        dict[str, Any]: created event dict
    """
    set_entity_keys(entity, incident_alert)
    entity_flat = dict_to_flat(entity.raw_data)
    set_event_product_keys(
        entity_flat,
        [entity_flat, flat_incident],
        product_field_fallback,
        fallback_logic_debug,
    )

    return entity_flat


def set_entity_keys(entity: AlertEntity, incident_alert: IncidentAlert):
    """
    Set entity keys

    Args:
        entity (AlertEntity): AlertEntity object
        incident_alert (IncidentAlert): IncidentAlert object
    """
    entity.raw_data[entity.kind] = entity.get_value()

    for key, value in incident_alert.raw_data["properties"].items():
        if isinstance(value, str) and is_date(value):
            entity.raw_data["properties"][key] = value


def set_event_product_keys(
    event_flat: dict[str, str],
    source_dicts: list[dict[str, str]],
    product_field_fallback: list[str],
    fallback_logic_debug: bool,
):
    """
    Set event product keys

    Args:
        event_flat (dict[str, str]): Flattened event data
        source_dicts (list[dict[str, str]]): List of flattened source dicts
        product_field_fallback (list[str]): List of product field name fallback fields
        fallback_logic_debug (bool): Specifies if fallback logic debug should be enabled
    """
    product_value, product_fallback_field = find_fallback_value(
        source_dicts=source_dicts, fallbacks_list=product_field_fallback
    )
    if product_fallback_field is not None:
        event_flat["product_type"] = product_value
        if fallback_logic_debug:
            event_flat["ProductFieldFallback"] = product_fallback_field


def create_scheduled_alert_events(
    flat_incident: dict[str, str],
    incident_alert: IncidentAlert,
    create_extra_events_for_all_entities: bool,
    product_field_fallback: list[str],
    fallback_logic_debug: bool,
) -> list[dict]:
    """
    Create scheduled alert events from events or entities

    Args:
        flat_incident (dict[str, str]): Flattened incident data
        incident_alert (IncidentAlert): IncidentAlert object
        create_extra_events_for_all_entities (bool):
            Specifies if events should be created for all entities
        product_field_fallback (list[str]): List of product field name fallback fields
        fallback_logic_debug (bool): Specifies if fallback logic debug should be enabled

    Returns:
        list[dict]: list of events dicts
    """
    events = []
    incident_alert_flat = incident_alert.to_event()

    events.extend(
        create_events_from_scheduled_alert_events(
            incident_alert,
            incident_alert_flat,
            flat_incident,
            product_field_fallback,
            fallback_logic_debug,
        )
    )

    events.extend(
        create_regular_alert_events(
            flat_incident,
            incident_alert,
            create_extra_events_for_all_entities,
            product_field_fallback,
            fallback_logic_debug,
        )
    )

    if not events:
        # If no events and entities -> use the alert itself as event
        events.append(
            create_event_from_alert(
                flat_incident,
                incident_alert,
                incident_alert_flat,
                product_field_fallback,
                fallback_logic_debug,
            )
        )

    return events


def create_events_from_scheduled_alert_events(
    incident_alert: IncidentAlert,
    incident_alert_flat: dict[str, str],
    flat_incident: dict[str, str],
    product_field_fallback: list[str],
    fallback_logic_debug: bool,
) -> list[dict[str, str]]:
    """
    Create events from scheduled alert events

    Args:
        incident_alert (IncidentAlert): IncidentAlert object
        incident_alert_flat (dict[str, str]): Flattened incident alert data
        flat_incident (dict[str, str]): Flattened incident data
        product_field_fallback (list[str]): List of product field name fallback fields
        fallback_logic_debug (bool): Specifies if fallback logic debug should be enabled

    Returns:
        list[dict[str, str]]: list of events
    """
    events = incident_alert.scheduled_alert.get_events_flat()

    for event in events:
        set_event_product_keys(
            event,
            [event, incident_alert_flat, flat_incident],
            product_field_fallback,
            fallback_logic_debug,
        )

        event["kind"] = (
            constants.NRT_ALERT_EVENT_KIND
            if incident_alert.scheduled_alert.product_component_name
            == constants.NRT_ALERT_TYPE_STRING
            else constants.SCHEDULED_ALERT_EVENT_KIND
        )

    return events


def create_event_from_alert(
    flat_incident: dict[str, str],
    incident_alert: IncidentAlert,
    incident_alert_flat: dict[str, str],
    product_field_fallback: list[str],
    fallback_logic_debug: bool,
) -> dict[str, str]:
    """
    Create event from alert

    Args:
        flat_incident (dict[str, str]): Flattened incident data
        incident_alert (IncidentAlert): IncidentAlert object
        incident_alert_flat (dict[str, str]): Flattened incident alert data
        product_field_fallback (list[str]): List of product field name fallback fields
        fallback_logic_debug (bool): Specifies if fallback logic debug should be enabled

    Returns:
        dict[str, str]: Flattened incident alert with additional keys
    """
    set_event_product_keys(
        incident_alert_flat,
        [incident_alert_flat, flat_incident],
        product_field_fallback,
        fallback_logic_debug,
    )

    incident_alert_flat["kind"] = (
        constants.NRT_ALERT_EVENT_KIND
        if incident_alert.scheduled_alert.product_component_name
        == constants.NRT_ALERT_TYPE_STRING
        else constants.SCHEDULED_ALERT_EVENT_KIND
    )

    return incident_alert_flat
