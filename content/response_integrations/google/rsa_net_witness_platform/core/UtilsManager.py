from __future__ import annotations
import datetime
from typing import List

from soar_sdk.SiemplifyUtils import convert_datetime_to_unix_time
from .constants import CONNECTOR_DATETIME_FORMAT, MAX_EVENTS_PER_ALERT


# Move to TIPCommon
def filter_old_alerts(
    logger, alerts, existing_ids, id_key="alert_id", event_count_key="event_count"
):
    """
    Filter alerts that were already processed
    :param logger: {SiemplifyLogger} Siemplify logger
    :param alerts: {list} List of Alert objects
    :param existing_ids: {list} List of ids to filter
    :param id_key: {str} The key of identifier
    :param event_count_key: {str} The key of event count
    :return: {list} List of filtered Alert objects
    """
    filtered_alerts = []
    for alert in alerts:
        id = getattr(alert, id_key)
        event_count = getattr(alert, event_count_key)
        existing_item = next(
            (item for item in existing_ids if item.get("id", "") == id), None
        )

        if not existing_item:
            filtered_alerts.append(alert)
        else:
            if existing_item.get("event_count") not in ["N/A", event_count]:
                filtered_alerts.append(alert)
            else:
                logger.info(f"The alert {id} skipped since it has been fetched before")

    return filtered_alerts


def convert_string_to_datetime(datetime_str: str) -> datetime.datetime:
    """
    Convert datetime string of format "2021-01-05T14:17:16.506Z" to datetime object
    :param datetime_str: {str} The datetime represented as string
    :return: {datetime.datetime} The converted datetime object
    """
    return datetime.datetime.strptime(datetime_str, CONNECTOR_DATETIME_FORMAT)


def convert_string_to_unix_time(datetime_str: str) -> int:
    """
    Convert datetime string of format "2021-01-05T14:17:16.506Z" to unix time in milliseconds.
    :param datetime_str: {str} The datetime represented as string
    :return: {int} the datetime represented as unix time in milliseconds
    """
    return convert_datetime_to_unix_time(convert_string_to_datetime(datetime_str))


def convert_datetime_to_string(datetime_obj: datetime.datetime) -> str:
    """
    Convert datetime object to string of format "2021-01-05T14:17:16.506Z"
    :param datetime_obj: {datetime.datetime} datetime.datetime object
    :return: {str} The datetime object represented as formatted string
    """
    return datetime_obj.strftime(CONNECTOR_DATETIME_FORMAT)


def limit_events_per_siemplify_alert(events: List[dict]) -> List[List[dict]]:
    """
    To ensure we don't ingest an alert with too many events, we divide the events into chunks of MAX_EVENTS_PER_ALERT (platform limitation)
    :param events: {list} List of events to be created for a Siemplify Alert
    :return: {[[dict]]} List of lists of events. Each list of events is of max size MAX_EVENTS_PER_ALERT
    """
    return [
        events[x : x + MAX_EVENTS_PER_ALERT]
        for x in range(0, len(events), MAX_EVENTS_PER_ALERT)
    ]


def convert_minutes_to_milliseconds(minutes: int) -> int:
    """
    Convert minutes to milliseconds
    :param minutes: {int} Minutes to be converted to milliseconds
    :return: {int} Equivalent amount in milliseconds
    """
    return minutes * 60 * 1000


def convert_milliseconds_to_minutes(milliseconds: int) -> float:
    """
    Convert milliseconds to minutes
    :param milliseconds: {int} Milliseconds to be converted to minutes
    :return: {int} Equivalent amount in minutes
    """
    return milliseconds / 60000
