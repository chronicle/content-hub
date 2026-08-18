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

import ast
import datetime
import time

import arrow

from soar_sdk.SiemplifyUtils import (
    convert_datetime_to_unix_time,
    convert_unixtime_to_datetime,
    unix_now,
    utc_now,
)
from TIPCommon.smp_io import read_ids_by_timestamp, write_ids_with_timestamp
from TIPCommon.transformation import (
    convert_list_to_comma_string,
    string_to_multi_value as str_to_multi_value,
)
from TIPCommon.utils import platform_supports_db


UNIX_FORMAT = 1
DATETIME_FORMAT = 2
STORED_IDS_LIMIT = 1000
TIMESTAMP_KEY = "timestamp"
IDS_KEY = "ids"


def save_query_timestamp(
    siemplify,
    query_alerts,
    force_save_timestamp=None,
    timestamp_key="timestamp",
    incrementation_value=0,
    log_timestamp=True,
    query_timestamp_filename="query_time.json",
):
    """
    Save last timestamp for given alerts
    :param siemplify: {siemplify} Siemplify object
    :param query_alerts: {dict} query with alerts to save
    :param force_save_timestamp: {dict} query with timestamp to save without events
    :param timestamp_key: {str} key for getting timestamp from alert
    :param incrementation_value: {int} The value to increment last timestamp by milliseconds
    :param log_timestamp: {bool} Whether log timestamp or not
    :param query_timestamp_filename: {str} file name
    :return: {bool} Is timestamp updated
    """
    if not platform_supports_db(siemplify):
        query_timestamps = read_ids_by_timestamp(
            siemplify, ids_file_name=query_timestamp_filename
        )
    else:
        query_timestamps = read_ids_by_timestamp(siemplify, db_key=TIMESTAMP_KEY)
    force_save_timestamp = force_save_timestamp or {}
    for query_id, alerts in query_alerts.items():
        forced_timestamp = force_save_timestamp.get(query_id)
        if forced_timestamp:
            siemplify.LOGGER.info(
                f"No alerts for {query_id}. Saving latest_time: {forced_timestamp}"
            )
            query_timestamps[query_id] = forced_timestamp
            continue
        if not alerts:
            if log_timestamp:
                siemplify.LOGGER.info(
                    f"Timestamp is not updated since no alerts fetched for {query_id}"
                )
            continue

        alerts.sort(key=lambda alert: int(getattr(alert, timestamp_key)))
        last_timestamp = int(getattr(alerts[-1], timestamp_key)) + incrementation_value
        # add or update existing
        query_timestamps[query_id] = last_timestamp

        if log_timestamp:
            siemplify.LOGGER.info(
                f"Last timestamp for query {query_id} is :{last_timestamp}"
            )

    if not platform_supports_db(siemplify):
        return write_ids_with_timestamp(
            siemplify, ids=query_timestamps, ids_file_name=query_timestamp_filename
        )
    else:
        return write_ids_with_timestamp(
            siemplify, ids=query_timestamps, db_key=TIMESTAMP_KEY
        )


def get_last_success_time_for_queries(
    siemplify,
    queries,
    offset_with_metric,
    time_format=UNIX_FORMAT,
    print_value=True,
    query_timestamp_filename="query_time.json",
):
    """
    Get last success run time for queries
    :param siemplify: {siemplify} Siemplify object
    :param connector_common_manager: {ConnectorCommonManagerForDbSystem or ConnectorCommonManagerForFileSystem} instance
    :param queries: {list} List of query
    :param offset_with_metric: {dict} metric and value. Ex {'hours': 1}
    :param time_format: {int} The format of the output time. Ex DATETIME, UNIX
    :param print_value: {bool} Whether log the value or not
    :param query_timestamp_filename: {str} file name
    :return: {dict} If first run, return current time in query dict minus offset time, else dict with saved timestamp
    """
    if not platform_supports_db(siemplify):
        last_run_query_timestamp = read_ids_by_timestamp(
            siemplify, ids_file_name=query_timestamp_filename
        )
    else:
        last_run_query_timestamp = read_ids_by_timestamp(
            siemplify, db_key=TIMESTAMP_KEY
        )
    offset = datetime.timedelta(**offset_with_metric)
    current_time = arrow.utcnow()
    queries_timestamp = {}

    for query_identifier in [get_query_identifier(query) for query in queries]:
        saved_time = last_run_query_timestamp.get(query_identifier)
        datetime_result = (
            convert_unixtime_to_datetime(saved_time)
            if saved_time
            else current_time - offset
        )
        unix_result = convert_datetime_to_unix_time(datetime_result)

        if print_value:
            siemplify.LOGGER.info(
                f'Last success time for query "{query_identifier}". '
                f"Date time: {datetime_result}. Unix: {unix_result}"
            )

        queries_timestamp[query_identifier] = (
            unix_result if time_format == UNIX_FORMAT else datetime_result
        )

    return queries_timestamp


def validate_timestamp(last_run_timestamp, offset_in_hours):
    """
    Validate timestamp in range
    :param last_run_timestamp: {datetime} last run timestamp
    :param offset_in_hours: {datetime} last run timestamp
    :return: {datetime} if first run, return current time minus offset time, else return timestamp from file
    """
    current_time = utc_now()
    # Check if first run
    if current_time - last_run_timestamp > datetime.timedelta(hours=offset_in_hours):
        return current_time - datetime.timedelta(hours=offset_in_hours)
    else:
        return last_run_timestamp


def convert_to_single_value_combinations(multi_value_dict, combinations=None):
    if combinations is None:
        combinations = []

    contains_only_single_values = True
    for key, values in multi_value_dict.items():
        if isinstance(values, list):
            contains_only_single_values = False
            for value in values:
                combinations = convert_to_single_value_combinations(
                    dict(multi_value_dict, **{key: value}), combinations
                )
            break
    if contains_only_single_values:
        combinations.append(multi_value_dict)

    return combinations


def get_less_possible_combinations(multi_value_dict):
    # calculate maximum length of multivalues
    result = []
    if not multi_value_dict:
        return result

    max_length = len(max(multi_value_dict.values(), key=len))
    for i in range(max_length):
        current_combination = {}
        for key, multi_value in multi_value_dict.items():
            try:
                current_combination[key] = multi_value[i]
            except IndexError:
                current_combination[key] = None
        result.append(current_combination)
    return result


# Move to TIPCommon
def filter_old_alerts(logger, alerts, existing_ids):
    """
    Filter alerts that were already processed
    :param logger: {SiemplifyLogger} Siemplify logger
    :param alerts: {list} The alerts to filter
    :param existing_ids: {list} The ids to filter
    :return: {list} The filtered alerts
    """
    filtered_alerts = []

    for alert in alerts:
        if alert.alert_id not in existing_ids.keys():
            filtered_alerts.append(alert)
        else:
            logger.info(
                f"The alert {alert.alert_id} skipped since it has been fetched before"
            )

    return filtered_alerts


def filter_old_alerts_from_list(logger, alerts, existing_ids, id_key="alert_id"):
    """
    Filter alerts that were already processed
    :param logger: {SiemplifyLogger} Siemplify logger
    :param alerts: {list} The alerts to filter
    :param existing_ids: {list} The ids to filter
    :param id_key: {unicode} The key of identifier
    :return: {list} The filtered alerts
    """
    filtered_alerts = []

    for alert in alerts:
        id = getattr(alert, id_key)
        if id not in existing_ids:
            filtered_alerts.append(alert)
        else:
            logger.info(f"The alert {id} skipped since it has been fetched before")

    return filtered_alerts


def get_query_identifier(query):
    """
    Get query identifier
    :return: {str} query identifier
    """
    return query


# Move to TIPCommon
def is_approaching_timeout(
    python_process_timeout, connector_starting_time, timeout_threshold=0.9
):
    """
    Check if a timeout is approaching.
    :param python_process_timeout: {int} The python process timeout
    :return: {bool} True if timeout is close, False otherwise
    """
    processing_time_ms = unix_now() - connector_starting_time
    return processing_time_ms > python_process_timeout * 1000 * timeout_threshold


def get_entity_original_identifier(entity):
    """
    Helper function for getting entity original identifier
    :param entity: entity from which function will get original identifier
    :return: {str} original identifier
    """
    return entity.additional_properties.get("OriginalIdentifier", entity.identifier)


def string_to_multi_value(string_value, delimiter=","):
    """
    String to multi value.
    :param string_value: {str} String value to convert multi value.
    :param delimiter: {str} Delimiter to extract multi values from single value string.
    :return: {dict} fixed dictionary.
    """
    if not string_value:
        return []
    return [
        single_value.strip()
        for single_value in string_value.split(delimiter)
        if single_value.strip()
    ]


def clean_duplicated_keys(target_dict):
    """
    To fix duplicated keys issue.
    :param target_dict: {dict} dictionary to fix.
    :return: {dict} fixed dictionary.
    """
    result_dict = {}
    count_dict = {}
    for key in target_dict.keys():
        if key.lower() in result_dict:
            if key.lower() in count_dict:
                count_dict[key.lower()] += 1
            else:
                count_dict.update({key.lower(): 0})
            result_dict[f"{key.lower}_{count_dict.get(key.lower())}"] = target_dict.get(
                key
            )
        else:
            result_dict[key.lower()] = target_dict.get(key)
    return result_dict


def wait_and_check_if_job_id_done(manager, sid, repeat=3):
    for i in range(repeat):
        if manager.is_job_done(sid=sid):
            return True
        time.sleep(3)

    return False


# Move to TIPCommon
WHITELIST_FILTER = 1
BLACKLIST_FILTER = 2


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


def get_splunk_queries(query: str) -> list[str]:
    """Parse a Splunk query string to retrieve individual queries.

    Args:
        query (str): A string containing one or more Splunk queries.

    Returns:
        list[str]: A list of individual Splunk queries extracted from the query string.

    Raises:
        ValueError: If unable to parse the query parameter values to retrieve individual
            queries.
    """
    if query.startswith("[") and query.endswith("]"):
        try:
            queries = convert_list_to_comma_string(ast.literal_eval(query))
            return str_to_multi_value(queries, only_unique=True)

        except SyntaxError as error:
            raise ValueError(
                'Unable to parse "Query" parameter values to retrieve individual '
                "queries."
            ) from error

    return [query]
