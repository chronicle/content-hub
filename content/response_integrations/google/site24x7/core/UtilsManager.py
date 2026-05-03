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
import os
import requests
import datetime
from soar_sdk.SiemplifyUtils import (
    utc_now,
    convert_datetime_to_unix_time,
    unix_now,
    convert_string_to_unix_time,
    convert_string_to_datetime,
)
from TIPCommon import validate_map_file
from EnvironmentCommon import EnvironmentHandle
from .Site24x7Exceptions import Site24x7Exception
from .constants import DEFAULT_TIME_FRAME, ERROR_WORD
from dateutil.tz import tzoffset


# Move to TIPCommon
STORED_IDS_LIMIT = 1000
TIMEOUT_THRESHOLD = 0.9
WHITELIST_FILTER = 1
BLACKLIST_FILTER = 2
UNIX_FORMAT = 1
DATETIME_FORMAT = 2


def convert_time_to_given_offset(time_param, utc_offset):
    """
    Converts time to given offset
    :param utc_offset: UTC offset
    :param time_param: Time to convert
    :return: {datetime}
    """
    return datetime.datetime(
        time_param.year,
        time_param.month,
        time_param.day,
        time_param.hour,
        time_param.minute,
        time_param.second,
        tzinfo=tzoffset(None, float(utc_offset) * 60 * 60),
    ) + datetime.timedelta(hours=utc_offset)


def validate_response(response, error_msg="An error occurred"):
    """
    Validate response
    :param response: {requests.Response} The response to validate
    :param error_msg: {unicode} Default message to display on error
    """
    try:
        response.raise_for_status()
        if ERROR_WORD in response.text.lower():
            raise Site24x7Exception(
                f"{error_msg}: {response.json().get(ERROR_WORD) or response.content}"
            )
    except requests.HTTPError as error:
        try:
            response.json()
        except Exception:
            raise Site24x7Exception(f"{error_msg}: {error} {error.response.content}")

        raise Site24x7Exception(
            f"{error_msg}: {error} {response.json().get('message') or response.content}"
        )


# Move to TIPCommon
def is_approaching_timeout(
    python_process_timeout, connector_starting_time, timeout_threshold=TIMEOUT_THRESHOLD
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


def get_last_success_time(
    siemplify,
    offset_with_metric,
    time_format=DATETIME_FORMAT,
    print_value=True,
    date_time_format=None,
):
    """
    Get last success time datetime
    :param siemplify: {siemplify} Siemplify object
    :param offset_with_metric: {dict} metric and value. Ex {"hours": 1}
    :param time_format: {int} The format of the output time. Ex DATETIME, UNIX
    :param print_value: {bool} Whether log the value or not
    :param date_time_format: {str} Datetime format to return data
    :return: {time} If first run, return current time minus offset time, else return timestamp from file
    """
    last_run_timestamp = siemplify.fetch_timestamp(datetime_format=True)
    offset = datetime.timedelta(**offset_with_metric)
    current_time = utc_now()
    # Check if first run
    raw_datetime = (
        current_time - offset
        if convert_datetime_to_unix_time(last_run_timestamp) == 0
        else last_run_timestamp
    )
    unix_result = convert_datetime_to_unix_time(raw_datetime)
    datetime_result = (
        raw_datetime
        if not date_time_format
        else raw_datetime.strftime(date_time_format)
    )

    if print_value:
        siemplify.LOGGER.info(
            f"Last success time. Date time:{datetime_result}. Unix:{unix_result}"
        )

    return unix_result if time_format == UNIX_FORMAT else datetime_result


# Move to TIPCommon
def get_environment_common(
    siemplify, environment_field_name, environment_regex_pattern, map_file="map.json"
):
    """
    Get environment common
    :param siemplify: {siemplify} Siemplify object
    :param environment_field_name: {str} The environment field name
    :param environment_regex_pattern: {str} The environment regex pattern
    :param map_file: {str} The map file
    :return: {EnvironmentHandle}
    """
    map_file_path = os.path.join(siemplify.run_folder, map_file)
    validate_map_file(siemplify, map_file_path)
    return EnvironmentHandle(
        map_file_path,
        siemplify.LOGGER,
        environment_field_name,
        environment_regex_pattern,
        siemplify.context.connector_info.environment,
    )


def filter_alerts_by_timestamp(
    logger, alerts, last_success_time, existing_ids, timestamp_key="sent_time"
):
    """
    Filter alerts that were already processed
    :param logger: {SiemplifyLogger} Siemplify logger
    :param alerts: {list} List of Alert objects
    :param last_success_time: {datetime} List of ids to filter
    :param existing_ids: {list} List of already ingested ids
    :param timestamp_key: {str} The key of timestamp
    :return: {list} List of filtered Alert objects
    """
    filtered_alerts = []
    last_success_date = last_success_time.replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    last_success_time = (
        (last_success_date - datetime.timedelta(days=DEFAULT_TIME_FRAME))
        if not existing_ids
        else last_success_time
    )

    for alert in alerts:
        timestamp = convert_string_to_datetime(getattr(alert, timestamp_key))

        if timestamp >= last_success_time:
            filtered_alerts.append(alert)
        else:
            logger.info(f"The alert {alert.msg} was already fetched. Skipping...")

    return filtered_alerts


# Move to TIPCommon
def filter_old_alerts(logger, alerts, existing_ids, id_key="id"):
    """
    Filter alerts that were already processed
    :param logger: {SiemplifyLogger} Siemplify logger
    :param alerts: {list} List of Alert objects
    :param existing_ids: {list} List of ids to filter
    :param id_key: {str} The key of identifier
    :return: {list} List of filtered Alert objects
    """
    filtered_alerts = []

    for alert in alerts:
        id = getattr(alert, id_key)

        if id not in existing_ids:
            filtered_alerts.append(alert)
        else:
            logger.info(f"The alert {id} skipped since it has been fetched before")

    return filtered_alerts


# Move to TIPCommon
def read_ids(siemplify, ids_file_name="ids.json"):
    """
    Read existing alerts IDs from ids file (from last 24h only)
    :param siemplify: {Siemplify} Siemplify object.
    :param ids_file_name: {str} The name of the ids file
    :return: {list} List of ids
    """
    ids_file_path = os.path.join(siemplify.run_folder, ids_file_name)

    if not os.path.exists(ids_file_path):
        return []

    try:
        with open(ids_file_path, "r") as f:
            return json.loads(f.read())
    except Exception as e:
        siemplify.LOGGER.error(f"Unable to read ids file: {e}")
        siemplify.LOGGER.exception(e)
        return []


# Move to TIPCommon
def write_ids(siemplify, ids, ids_file_name="ids.json"):
    """
    Write ids to the ids file
    :param siemplify: {Siemplify} Siemplify object.
    :param ids: {list} The ids to write to the file
    :param ids_file_name: {str} The name of the ids file.
    :return: {bool}
    """
    ids = ids[-STORED_IDS_LIMIT:]

    try:
        ids_file_path = os.path.join(siemplify.run_folder, ids_file_name)

        if not os.path.exists(os.path.dirname(ids_file_path)):
            os.makedirs(os.path.dirname(ids_file_path))

        with open(ids_file_path, "w") as f:
            try:
                for chunk in json.JSONEncoder().iterencode(ids):
                    f.write(chunk)
            except:
                # Move seeker to start of the file
                f.seek(0)
                # Empty the content of the file (the partially written content that was written before the exception)
                f.truncate()
                # Write an empty dict to the events data file
                f.write("[]")
                raise

        siemplify.LOGGER.info(f"Write ids. Total ids={len(ids)}")
        return True

    except Exception as e:
        siemplify.LOGGER.error(f"Failed writing IDs to IDs file, ERROR: {e}")
        siemplify.LOGGER.exception(e)
        return False


# Move to TIPCommon
def is_overflowed(siemplify, alert_info, is_test_run):
    """
    Check if overflowed
    :param siemplify: {Siemplify} Siemplify object.
    :param alert_info: {AlertInfo}
    :param is_test_run: {bool} Whether test run or not.
    :return: {bool}
    """
    try:
        return siemplify.is_overflowed_alert(
            environment=alert_info.environment,
            alert_identifier=alert_info.ticket_id,
            alert_name=alert_info.rule_generator,
            product=alert_info.device_product,
        )

    except Exception as e:
        siemplify.LOGGER.error(f"Error validation connector overflow, ERROR: {e}")
        siemplify.LOGGER.exception(e)

        if is_test_run:
            raise

    return False


def save_timestamp(
    siemplify,
    alerts,
    timestamp_key="timestamp",
    incrementation_value=0,
    log_timestamp=True,
):
    """
    Save last timestamp for given alerts
    :param siemplify: {Siemplify} Siemplify object
    :param alerts: {list} The list of alerts to find the last timestamp
    :param timestamp_key: {str} key for getting timestamp from alert
    :param incrementation_value: {int} The value to increment last timestamp by milliseconds
    :param log_timestamp: {bool} Whether log timestamp or not
    :return: {bool} Is timestamp updated
    """
    if not alerts:
        siemplify.LOGGER.info("Timestamp is not updated since no alerts fetched")
        return False

    alerts = sorted(alerts, key=lambda alert: getattr(alert, timestamp_key))
    alert_timestamp = getattr(alerts[-1], timestamp_key)
    save_utc_offset(
        siemplify,
        convert_string_to_datetime(alert_timestamp).utcoffset().total_seconds()
        / 60
        / 60,
    )
    last_timestamp = convert_string_to_unix_time(alert_timestamp) + incrementation_value

    if log_timestamp:
        siemplify.LOGGER.info(f"Last timestamp is: {last_timestamp}")

    siemplify.save_timestamp(new_timestamp=last_timestamp)
    return True


def save_utc_offset(siemplify, utc_offset, uts_offset_file_name="utc_offset.json"):
    """
    Write utc_offset value to the file
    :param siemplify: {Siemplify} Siemplify object.
    :param utc_offset: {float} The UTC offset to write to the file.
    :param uts_offset_file_name: {str} The name of the file.
    :return: {bool}
    """
    try:
        utc_offset_file_path = os.path.join(siemplify.run_folder, uts_offset_file_name)

        if not os.path.exists(os.path.dirname(utc_offset_file_path)):
            os.makedirs(os.path.dirname(utc_offset_file_path))

        with open(utc_offset_file_path, "w") as f:
            try:
                f.write(str(utc_offset))
            except:
                f.write("")
                raise

        siemplify.LOGGER.info(f"UTC offset {utc_offset} is saved in file.")
        return True

    except Exception as e:
        siemplify.LOGGER.error(f"Failed writing UTC offset to file, ERROR: {e}")
        siemplify.LOGGER.exception(e)
        return False


def read_utc_offset(siemplify, uts_offset_file_name="utc_offset.json"):
    """
    Read UTC offset from file
    :param siemplify: {Siemplify} Siemplify object.
    :param uts_offset_file_name: {str} The name of the file.
    :return: {float} UTC offset
    """
    utc_offset_file_path = os.path.join(siemplify.run_folder, uts_offset_file_name)

    if not os.path.exists(utc_offset_file_path):
        return 0

    try:
        with open(utc_offset_file_path, "r") as f:
            return float(f.read())
    except Exception as e:
        siemplify.LOGGER.error(f"Unable to read UTC offset file: {e}")
        siemplify.LOGGER.exception(e)
        return 0


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
