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
import os
import arrow
import pytz
from soar_sdk.SiemplifyUtils import unix_now
from .constants import (
    DEFAULT_RESULTS_LIMIT,
    TIME_FORMAT,
    WHITELIST_FILTER,
    BLACKLIST_FILTER,
)
from TIPCommon import read_content

STORED_IDS_LIMIT = 5000
TIMEOUT_THRESHOLD = 0.9
GLOBAL_TIMEOUT_THRESHOLD_IN_MIN = 1

TIMESTAMP_FILE = "timestamp.stmp"
TIMESTAMP_KEY = "timestamp"


class PathIsNotWritable(Exception):
    pass


def save_timestamp_arrow(
    siemplify, alerts, timestamp_key="timestamp", log_timestamp=True
):
    """
    Save last timestamp for given alerts
    :param siemplify: {Siemplify} Siemplify object
    :param alerts: {list} The list of alerts to find the last timestamp
    :param timestamp_key: {str} key for getting timestamp from alert
    :param log_timestamp: {bool} Whether log timestamp or not
    :return: {bool} Tuple - Is timestamp updated
    instead
    """
    if not alerts:
        siemplify.LOGGER.info("Timestamp is not updated since no alerts fetched")
        return False
    alerts = sorted(alerts, key=lambda alert: getattr(alert, timestamp_key))
    last_timestamp = getattr(alerts[-1], timestamp_key)
    if log_timestamp:
        siemplify.LOGGER.info(f"Last timestamp is :{last_timestamp}")

    siemplify.save_timestamp(new_timestamp=last_timestamp)
    return True


def get_entity_original_identifier(entity):
    """
    Helper function for getting entity original identifier
    :param entity: entity from which function will get original identifier
    :return: {str} original identifier
    """
    return entity.additional_properties.get("OriginalIdentifier", entity.identifier)


def is_approaching_timeout(connector_starting_time, python_process_timeout):
    """
    Check if a timeout is approaching.
    :param connector_starting_time: {int} Connector start time
    :param python_process_timeout: {int} The python process timeout
    :return: {bool} True if timeout is close, False otherwise
    """
    processing_time_ms = unix_now() - connector_starting_time
    return processing_time_ms > python_process_timeout * 1000 * TIMEOUT_THRESHOLD


def pass_whitelist_filter(siemplify, whitelist_as_a_blacklist, model, model_key):
    # whitelist filter
    whitelist = (
        siemplify.whitelist
        if isinstance(siemplify.whitelist, list)
        else [siemplify.whitelist]
    )
    whitelist_filter_type = (
        BLACKLIST_FILTER if whitelist_as_a_blacklist else WHITELIST_FILTER
    )
    model_value = getattr(model, model_key)
    if whitelist:
        if whitelist_filter_type == BLACKLIST_FILTER and model_value in whitelist:
            siemplify.LOGGER.info(f"'{model_value}' did not pass blacklist filter.")
            return False

        if whitelist_filter_type == WHITELIST_FILTER and model_value not in whitelist:
            siemplify.LOGGER.info(f"'{model_value}' did not pass whitelist filter.")
            return False

    return True


def convert_naive_datetime_to_aware_utc(naive_datetime):
    """
    Convert naive datetime to aware with UTC timezone
    :param naive_datetime: {datetime.datetime} Naive datetime
    :return: {datetime.datetime} Aware datetime
    """
    return naive_datetime.replace(tzinfo=pytz.utc)


def get_validated_limit(siemplify, number, number_replacer=DEFAULT_RESULTS_LIMIT):
    if number <= 0:
        siemplify.LOGGER.info(
            f"Number is not a positive. Use replacer {number_replacer}"
        )
        return number_replacer
    return number


def validate_positive_integer(number, err_msg="Limit parameter should be positive"):
    if number <= 0:
        raise Exception(err_msg)


def save_attachment(path, name, content):
    """
    Save attachment to local path
    :param path: {str} Path of the folder, where files should be saved
    :param name: {str} File name to be saved
    :param content: {str} File content
    :return: {str} Path to the downloaded files
    """
    # Create path if not exists
    if not os.path.exists(path):
        os.makedirs(path)
    # File local path
    local_path = os.path.join(path, name)
    with open(local_path, "wb") as file:
        file.write(content)
        file.close()

    return local_path


def validate_local_path(local_path):
    try:
        tmp_file_name = "tmp_file"
        save_attachment(local_path, tmp_file_name, b"")
        os.remove(os.path.join(local_path, tmp_file_name))
    except Exception as e:
        raise PathIsNotWritable(f'Path "{local_path}" is not writable. {e}')


# Use TIPCommon's
def string_to_multi_value(string_value, delimiter=",", only_unique=False):
    """
    String to multi value.
    @param string_value: {str} String value to convert multi value.
    @param delimiter: {str} Delimiter to extract multi values from single value string.
    @param only_unique: {bool} include only unique values
    """
    if not string_value:
        return []
    values = [
        single_value.strip()
        for single_value in string_value.split(delimiter)
        if single_value.strip()
    ]
    if only_unique:
        seen = set()
        return [value for value in values if not (value in seen or seen.add(value))]
    return values


def is_async_action_global_timeout_approaching(siemplify, start_time):
    return (
        siemplify.execution_deadline_unix_time_ms - start_time
        < GLOBAL_TIMEOUT_THRESHOLD_IN_MIN * 60
    )


def validate_files(files):
    for file in files:
        try:
            with open(file) as fp:
                pass
        except IOError:
            raise


def get_filtered_alerts(alerts, existing_ids):
    """
    Filter ids that were already processed
    :param alerts: {list} The alerts to filter
    :param existing_ids: {list} The ids to filter
    :return: {list} The filtered ids
    """
    filtered_alerts = []

    for alert in alerts:
        if alert.id not in existing_ids:
            filtered_alerts.append(alert)

    return filtered_alerts


def fetch_timestamp(siemplify):
    """
    Fetch RFC-3999 formatted timestamp from timestamp file.
    NOTICE! This is done because Siemplify SDK fetch_timestamp always
    converts the timestamps to unix in its internals. Unixtime is not
    accurate enough and doesn't contain the microseconds resolution.
    :return: {str} RFC-3999 formatted timestamp
    """

    return read_content(
        siemplify, TIMESTAMP_FILE, TIMESTAMP_KEY, arrow.get(0).isoformat("T") + "Z"
    )


def validate_timestamp_arrow(timestamp, max_days_backwards=1):
    """
    Adjust timestamp to the max days backwards value.
    :param timestamp: {str} RFC-3999 formatted timestamp.
    :param max_days_backwards: {int} days backwards to check timestamp.
    :return: {str} RFC-3999 formatted timestamp
    """
    # Calculate- Days backwards to milliseconds.
    offset_datetime = arrow.utcnow().shift(days=-max_days_backwards)

    # Calculate max time with offset.
    if timestamp < offset_datetime.datetime.strftime(TIME_FORMAT):
        return offset_datetime.datetime.strftime(TIME_FORMAT)

    return timestamp
