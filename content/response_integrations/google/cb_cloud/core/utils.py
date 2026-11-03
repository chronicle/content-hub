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

import copy
from soar_sdk.SiemplifyUtils import unix_now
from TIPCommon.smp_io import read_content, write_content
from .constants import (
    ALERT_NAME_ALLOWED_VALUE,
    BACKLOG_FILE,
    BACKLOG_DB_KEY,
    EVENTS_COUNT_TRACKING_FILE,
    EVENTS_COUNT_TRACKING_DB_KEY,
    EVENTS_COUNT_TRACKING_TS_KEY,
    EVENTS_COUNT_TRACKING_COUNT_KEY,
    KEY_FOR_SAVED_ALERTS,
    KEY_FOR_SAVED_EVENTS,
    KEY_FOR_SAVED_EVENTS_TIME,
    KEY_FOR_UPDATED_ALERTS_TIME,
    OFFENSE_EVENTS_FILE,
    OFFENSE_EVENTS_DB_KEY,
    PLACEHOLDER_START,
    PLACEHOLDER_END,
)
import arrow
from . import datamodels
from .exceptions import ParameterValidationException, CBCloudException


class LOGGER:
    def __init__(self, logger):
        self.logger = logger

    def info(self, msg):
        if self.logger:
            self.logger.info(msg)


UNIX_FORMAT = 1
DATETIME_FORMAT = 2
STORED_IDS_LIMIT = 1000
TIMEOUT_THRESHOLD = 0.9


# Move to TIPCommon
WHITELIST_FILTER = 1
BLACKLIST_FILTER = 2


def read_offense_events(siemplify, empty_data={}):
    """
    Load already seen events of rules and offenses.
    :return: {dict} The offense events, in the following format:
    {
          "{alert ID with legacy ID}":
          {
              "last_update_time": "unix time",
              "events": {
                "0A65C62595A803AF6A07AD9EC5D88D2921795387": {
                    "timestamp": unixtime
                }
              }
          }
        }
    """

    event_ids = read_content(
        siemplify, OFFENSE_EVENTS_FILE, OFFENSE_EVENTS_DB_KEY, empty_data
    )
    # if not event_ids:
    if event_ids == empty_data:
        siemplify.LOGGER.info(
            f"Connector will discard saved events and continue with empty alerts ids store."
        )
    else:
        try:
            event_ids = event_ids.get(KEY_FOR_SAVED_ALERTS)
        except Exception as e:
            siemplify.LOGGER.info(f"Could not extract event ids from file: {e}")
            siemplify.LOGGER.info(f"returned event ids: {event_ids}")
    return event_ids


def read_backlog_ids(siemplify, alerts_backlog_timer):
    """
    read backlog alerts from either database or local file - dependent on the common_manager instance
    :param alerts_backlog_timer: {int} Alerts Backlog Timer
    :return: {(dict,dict)} (backlog alert ids filtered by backlog_timer, all backlog alert ids in the past 500 hours)
    """
    ids = total_alert_ids = read_content(siemplify, BACKLOG_FILE, BACKLOG_DB_KEY)
    try:
        ids = filter_old_ids_by_timestamp(
            ids=ids,
            offset_in_hours=alerts_backlog_timer / 60,
            convert_to_milliseconds=True,
            offset_is_in_days=False,
        )
    except Exception as e:
        siemplify.LOGGER.error(f"Unable to read backlog ids file: {e}")
        siemplify.LOGGER.exception(e)
    try:
        total_alert_ids = filter_old_ids_by_timestamp(
            ids=total_alert_ids,
            offset_in_hours=500,
            convert_to_milliseconds=True,
            offset_is_in_days=False,
        )
    except Exception as e:
        siemplify.LOGGER.error(f"Unable to read backlog ids file: {e}")
        siemplify.LOGGER.exception(e)

    expired_alerts = list(set(total_alert_ids) - set(ids))
    if expired_alerts:
        siemplify.LOGGER.info(
            f'The following backlog alerts are expired:{", ".join(expired_alerts)}'
        )
    siemplify.LOGGER.info(f"Loaded {len(ids)} valid backlog alerts")
    return ids, total_alert_ids


def read_events_count_tracking(siemplify, events_padding_period):
    events_count_tracking_data = read_content(
        siemplify, EVENTS_COUNT_TRACKING_FILE, EVENTS_COUNT_TRACKING_DB_KEY, {}
    )

    discard_time_unix = unix_now() - events_padding_period * 60 * 60 * 1000 * 1.25

    if not events_count_tracking_data:
        siemplify.LOGGER.info(
            f"No events count tracking data was found, proceeding with empty dict"
        )
    else:
        original_dict = events_count_tracking_data.copy()
        for alert_id, alert_tracking_data in original_dict.items():
            if alert_tracking_data[EVENTS_COUNT_TRACKING_TS_KEY] < discard_time_unix:
                del events_count_tracking_data[alert_id]
        discarded_alert_ids = (
            alert_id
            for alert_id in original_dict
            if alert_id not in events_count_tracking_data
        )
        if discarded_alert_ids:
            siemplify.LOGGER.info(
                f"Following alerts has exceeded events padding period and were removed from "
                f'events count tracking: {",".join(discarded_alert_ids)}'
            )
    return events_count_tracking_data


def save_events(
    siemplify,
    alerts_with_event_ids,
    existing_events,
    events_padding_period,
    offset_time_in_hours,
    empty_data,
):
    for (alert_id, last_update_time_ms), event_ids in alerts_with_event_ids.items():
        alert_exist = True

        if alert_id not in existing_events:
            siemplify.LOGGER.info(
                f"Alert {alert_id} was not found in json file. Creating new record"
            )
            existing_events[alert_id] = {
                KEY_FOR_UPDATED_ALERTS_TIME: last_update_time_ms,
                KEY_FOR_SAVED_EVENTS: {},
            }
            alert_exist = False

        for event_id in event_ids:
            if event_id not in existing_events[alert_id][KEY_FOR_SAVED_EVENTS]:
                existing_events[alert_id][KEY_FOR_SAVED_EVENTS][event_id] = {
                    KEY_FOR_SAVED_EVENTS_TIME: unix_now()
                }
                if alert_exist:
                    siemplify.LOGGER.info(
                        f"Event {event_id} found to be new for alert {alert_id} in "
                        f"json file."
                    )
    write_content(
        siemplify,
        {
            KEY_FOR_SAVED_ALERTS: filter_old_offense_events(
                existing_events, events_padding_period, offset_time_in_hours
            )
        },
        OFFENSE_EVENTS_FILE,
        OFFENSE_EVENTS_DB_KEY,
        empty_data,
    )


def save_events_count_tracking(
    siemplify, alerts_with_event_ids, events_padding_period, events_count_tracking_data
):
    for (alert_id, last_update_time_ms), event_ids in alerts_with_event_ids.items():

        if alert_id not in events_count_tracking_data:
            siemplify.LOGGER.info(
                f"Alert {alert_id} was not found in events count tracking file. Creating new record"
            )
            events_count_tracking_data[alert_id] = {
                EVENTS_COUNT_TRACKING_COUNT_KEY: 0,
                EVENTS_COUNT_TRACKING_TS_KEY: last_update_time_ms,
            }

        events_count_tracking_data[alert_id][EVENTS_COUNT_TRACKING_COUNT_KEY] += len(
            event_ids
        )
        siemplify.LOGGER.info(
            f"Alert {alert_id} was updated with new number of total alerts "
            f"{events_count_tracking_data[alert_id][EVENTS_COUNT_TRACKING_COUNT_KEY]} "
            f"in events count tracking file"
        )

    write_content(
        siemplify,
        events_count_tracking_data,
        EVENTS_COUNT_TRACKING_FILE,
        EVENTS_COUNT_TRACKING_DB_KEY,
        {},
    )


def filter_old_offense_events(
    existing_events, events_padding_period, offset_time_in_hours
):
    filtered_offense_events = copy.deepcopy(existing_events)
    time_limit = (
        arrow.utcnow()
        .shift(hours=-5 * max(events_padding_period, offset_time_in_hours))
        .timestamp()
        * 1000
    )

    for alert_id in existing_events.keys():
        for event_id, event_info in existing_events[alert_id][
            KEY_FOR_SAVED_EVENTS
        ].items():
            if event_info.get(KEY_FOR_SAVED_EVENTS_TIME, 1) < time_limit:
                del filtered_offense_events[alert_id][KEY_FOR_SAVED_EVENTS][event_id]

    return filtered_offense_events


def filter_old_alerts(existing_alerts, offset_time_in_hours):
    filtered_existing_alerts = copy.deepcopy(existing_alerts)

    time_limit = arrow.utcnow().shift(
        hours=-5 * offset_time_in_hours
    ).timestamp() * 1000

    for alert_id, timestamp in existing_alerts.items():
        if timestamp < time_limit:
            del filtered_existing_alerts[alert_id]

    return filtered_existing_alerts


def save_alerts(
    siemplify, existing_alerts, processed_alert_ids, offset_time_in_hours, empty_data={}
):
    for alert_id in processed_alert_ids:
        existing_alerts[alert_id] = unix_now()
    write_content(
        siemplify,
        {
            KEY_FOR_SAVED_ALERTS: filter_old_alerts(
                existing_alerts, offset_time_in_hours
            )
        },
        OFFENSE_EVENTS_FILE,
        OFFENSE_EVENTS_DB_KEY,
        empty_data,
    )


def save_backlog_ids(siemplify, backlog_ids_to_process, new_backlog_alerts):
    """
    write backlog alerts to either database or local file - dependent on the common_manager instance
    :param backlog_ids_to_process: {dict} processed backlog alert ids
    :param new_backlog_alerts: {dict} new backlog alert ids
    """

    siemplify.LOGGER.info(
        f"Saving {len(backlog_ids_to_process)} existing and {len(new_backlog_alerts)} new backlog "
        f"alerts"
    )
    data = backlog_ids_to_process.copy()
    data.update(
        {
            alert.legacy_alert_id: arrow.utcnow().timestamp() * 1000
            for alert in new_backlog_alerts
        }
    )
    write_content(siemplify, data, BACKLOG_FILE, BACKLOG_DB_KEY)


def get_entity_original_identifier(entity):
    """
    Helper function for getting entity original identifier
    :param entity: entity from which function will get original identifier
    :return: {str} original identifier
    """
    return entity.additional_properties.get("OriginalIdentifier", entity.identifier)


def add_alert_to_backlog(siemplify, new_backlog_alerts, alert):
    if not alert.has_events:
        siemplify.LOGGER.info(
            f'Alert "{alert.id_for_logging}" can not have additional events. '
            f"Will not be added to backlog"
        )
        return new_backlog_alerts
    if alert.legacy_alert_id in [a.legacy_alert_id for a in new_backlog_alerts]:
        siemplify.LOGGER.info(f'Alert "{alert.id_for_logging}" already in backlog')
    else:
        siemplify.LOGGER.info(f'Adding alert "{alert.id_for_logging}" to backlog')
        new_backlog_alerts.append(alert)

    return new_backlog_alerts


def is_blacklisted(alert, blacklist):
    if blacklist:
        return alert.category in blacklist

    return False


def pass_filters(
    siemplify,
    alert: datamodels.Alert,
    watchlist_name_filter: list,
    alert_reputations_to_ingest: list = None,
) -> bool:
    """
    Determine if an alert passes the specified filters.

    Args:
        siemplify: The Siemplify instance used for logging and interaction.
        alert(datamodels.Alert): The alert object containing information about alert.
        alert_reputations_to_ingest (list): A list of reputations that the alert's
            threat cause reputation must match.
        watchlist_name_filter (list): A list of watchlist names that alert must pass.

    Returns:
        bool: True if the alert passes all filters, False otherwise.
    """
    if alert_reputations_to_ingest is not None:
        if alert.threat_cause_reputation not in alert_reputations_to_ingest:
            siemplify.LOGGER.info(
                f'Alert "{alert.id_with_legacy_id}" with reputation '
                f"{alert.threat_cause_reputation} did not pass reputation filter. "
                "Skipping..."
            )
            return False

    if not alert.pass_watchlist_filter(watchlist_name_filter):
        siemplify.LOGGER.info(
            f"Alert with watchlist name(s) '{','.join(alert.watchlists_names)}' did not pass watchlist filter."
        )
        return False

    return True


def backlog_ids_exists(backlog_ids_to_process):
    return len(backlog_ids_to_process) > 0


def remove_backlog_alert_by_id(siemplify, backlog_ids_to_process, backlog_alert_id):
    try:
        del backlog_ids_to_process[backlog_alert_id]
        siemplify.LOGGER.info(
            f'Alert "{backlog_alert_id}" successfully removed from backlog.'
        )
    except:
        siemplify.LOGGER.info(
            f'Can not remove alert "{backlog_alert_id}" from backlog.'
        )


def remove_backlog_alert(siemplify, backlog_ids_to_process, backlog_alert):
    try:
        del backlog_ids_to_process[backlog_alert.legacy_alert_id]
        siemplify.LOGGER.info(
            f'Alert "{backlog_alert.id_for_logging}" successfully removed from backlog.'
        )
    except:
        siemplify.LOGGER.info(
            f'Can not remove alert "{backlog_alert.id_for_logging}" from backlog.'
        )

    return backlog_ids_to_process


def add_events_to_alert_info(alert_info, events, alert_id):
    if not events:
        raise CBCloudException(f'No new events were found for alert "{alert_id}"')
    alert_info.events = [event.as_event() for event in events]
    return alert_info


def is_approaching_timeout(
    python_process_timeout, connector_starting_time, timeout_threshold=0.9
):
    """
    Check if a timeout is approaching.
    :param python_process_timeout: {int} The python process timeout
    :param connector_starting_time: {int} The connector start unix time
    :param timeout_threshold: {int} Determines which part of the execution time is available for execution
    :return: {bool} True if timeout is close, False otherwise
    """
    processing_time_ms = unix_now() - connector_starting_time
    return processing_time_ms > python_process_timeout * 1000 * timeout_threshold


def priority_text_to_value(priority_text):
    supported_priorities = {
        "info": -1,
        "low": 40,
        "medium": 60,
        "high": 80,
        "critical": 100,
    }
    priority_value = supported_priorities.get(priority_text.lower())
    if not priority_value:
        raise Exception(f"Severity {priority_text} not supported")

    return priority_value


def pass_whitelist_filter(
    siemplify, whitelist_as_a_blacklist, model, model_key, whitelist=None
):
    # whitelist filter
    whitelist = whitelist or siemplify.whitelist
    whitelist_filter_type = (
        BLACKLIST_FILTER if whitelist_as_a_blacklist else WHITELIST_FILTER
    )
    model_value = getattr(model, model_key)
    model_values = model_value if isinstance(model_value, list) else [model_value]
    if whitelist:
        for value in model_values:
            if whitelist_filter_type == BLACKLIST_FILTER and value in whitelist:
                siemplify.LOGGER.info(f"'{value}' did not pass blacklist filter.")
                return False

            if whitelist_filter_type == WHITELIST_FILTER and value not in whitelist:
                siemplify.LOGGER.info(f"'{value}' did not pass whitelist filter.")
                return False

    return True


def pass_watchlist_filter(alert, watchlist_name_filter):
    """
    Pass watchlist filter.
    :param alert: {Alert} Alert to apply watchlist filter.
    :param watchlist_name_filter: {str} watchlist filter name
    :return: {bool} True if pass the watchlist filter.
    """
    if not alert.is_watchlist_type():
        return True

    if not watchlist_name_filter:
        return True

    return bool(
        [
            watchlist_name
            for watchlist_name in alert.watchlists_names
            if watchlist_name in watchlist_name_filter
        ]
    )


def validate_alert_name_field_name(alert_name_field_name):
    if alert_name_field_name not in ALERT_NAME_ALLOWED_VALUE:
        raise ParameterValidationException(
            f"Valid values to use for the Name Field of Siemplify Alert are {', '.join(ALERT_NAME_ALLOWED_VALUE)}"
        )


def validate_rule_generator_field_name(rule_generator_field_name):
    if rule_generator_field_name not in ALERT_NAME_ALLOWED_VALUE:
        raise ParameterValidationException(
            f"Valid values to use for the Rule Generator Field of Siemplify Alert are {', '.join(ALERT_NAME_ALLOWED_VALUE)}"
        )


def remove_none_values(origin_dict):
    """
    Remove keys from dictionary that has the value None
    :param origin_dict: {dict} Dictionary to process
    :return: {dict} Dictionary without keys that have the value None
    """
    return {k: v for k, v in origin_dict.items() if v is not None}


def transform_template_string(template, data):
    """
    Transform string containing template using provided data
    :param template: {str} string containing template
    :param data: {dict} data to use for transformation
    :return: {str} transformed string
    """
    index = 0

    while PLACEHOLDER_START in template[index:] and PLACEHOLDER_END in template[index:]:
        partial_template = template[index:]
        start, end = partial_template.find(PLACEHOLDER_START) + len(
            PLACEHOLDER_START
        ), partial_template.find(PLACEHOLDER_END)
        substring = partial_template[start:end]
        value = str(data.get(substring)) if data.get(substring) else ""
        template = template.replace(
            f"{PLACEHOLDER_START}{substring}{PLACEHOLDER_END}", value, 1
        )
        index = index + start + len(value)

    return template


def convert_comma_separated_to_list(comma_separated):
    """
    Convert comma-separated string to list
    :param comma_separated: String with comma-separated values
    :return: List of values
    """
    return (
        [item.strip() for item in comma_separated.split(",")] if comma_separated else []
    )


def convert_list_to_comma_string(values_list):
    """
    Convert list to comma-separated string
    :param values_list: List of values
    :return: String with comma-separated values
    """
    return (
        ", ".join(str(v) for v in values_list)
        if values_list and isinstance(values_list, list)
        else values_list
    )


def filter_old_ids_by_timestamp(
    ids,
    offset_in_hours,
    convert_to_milliseconds,
    offset_is_in_days
):
    """Filters ids that are older than IDS_HOURS_LIMIT hours.

    Args:
        ids: (dict) The ids to filter.
        offset_in_hours: (int) The IDs time limit (offset value) in hours.
        offset_is_in_days: (bool) If the offset supplied to this method is in days,
            please mark this as True for converting the offset days into hours.
        convert_to_milliseconds: (bool) Transform each ID's timestamp (unix) from
            seconds to milliseconds.

    Returns:
        (dict) The filtered ids.
    """
    filtered_ids = {}
    milliseconds = 1000 if convert_to_milliseconds else 1

    if offset_is_in_days:
        offset_in_hours = offset_in_hours * 24

    for alert_id, timestamp in ids.items():
        if timestamp > arrow.utcnow().shift(
            hours=-offset_in_hours
        ).timestamp() * milliseconds:
            filtered_ids[alert_id] = timestamp

    return filtered_ids
