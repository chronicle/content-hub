from __future__ import annotations
import requests
import json
import os
import datetime
from TIPCommon import validate_map_file
from EnvironmentCommon import EnvironmentHandle
from soar_sdk.SiemplifyUtils import (
    convert_string_to_datetime,
    convert_timezone,
    unix_now,
    convert_datetime_to_unix_time,
    utc_now,
)
import xmltodict
from .FortiSIEMExceptions import FortiSIEMErrorResponseException
from .constants import TIMEFRAME_MAPPING

# Move to TIPCommon
STORED_IDS_LIMIT = 3000
TIMEOUT_THRESHOLD = 0.9
WHITELIST_FILTER = 1
BLACKLIST_FILTER = 2
UNIX_FORMAT = 1
DATETIME_FORMAT = 2


def validate_response(response, error_msg="An error occurred"):
    """
    Validate response
    :param response: {requests.Response} The response to validate
    :param error_msg: {str} Default message to display on error
    """
    try:
        response.raise_for_status()
        json_result = {}

        try:
            json_result = xml_to_json(response.text)

        except Exception:
            pass

        if json_result.get("response", {}).get("error", {}).get("description", ""):
            raise FortiSIEMErrorResponseException(
                json_result.get("response", {}).get("error", {}).get("description")
            )

    except FortiSIEMErrorResponseException as e:
        raise Exception(e)
    except requests.HTTPError as error:
        if response.status_code == 400 or response.status_code == 404:
            raise Exception(error.response.text)

        raise Exception(f"{error_msg}: {error} {error.response.content}")

    return True


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


# Move to TIPCommon
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
        if current_time - last_run_timestamp > offset
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


def filter_old_alerts(
    logger,
    alerts,
    existing_ids,
    id_key="alert_id",
    events_limit=None,
    track_new_events=True,
    track_new_events_threshold=None,
):
    """
    Filter alerts that were already processed
    :param logger: {SiemplifyLogger} Siemplify logger
    :param alerts: {list} List of Alert objects
    :param existing_ids: {dict} existing ids json
    :param id_key: {str} The key of identifier
    :param events_limit: {int} Limit for incidents events
    :param track_new_events: {bool} Specifies if incidents new events should be tracked
    :param track_new_events_threshold: {int} Specifies how long incidents new events should be tracked
    :return: {list} List of filtered Alert objects
    """
    filtered_alerts = []

    for alert in alerts:
        id = getattr(alert, id_key)

        if not track_new_events:
            if id not in existing_ids.keys():
                filtered_alerts.append(alert)
            else:
                logger.info(f"The alert {id} skipped since it has been fetched before")
                continue
        else:
            if id not in existing_ids:
                filtered_alerts.append(alert)
            else:
                if alert.incident_last_seen == existing_ids.get(id, {}).get(
                    "first_seen"
                ):
                    logger.info(
                        f"The alert {id} skipped since it has been fetched before"
                    )
                    continue

                if unix_now() - existing_ids.get(id, {}).get(
                    "first_seen"
                ) > convert_hours_to_milliseconds(track_new_events_threshold):
                    logger.info(
                        f"The alert {id} skipped since it has been fetched before and time for waiting new "
                        f"events is expired"
                    )
                    continue
                if len(existing_ids.get(id, {}).get("event_ids", [])) >= events_limit:
                    logger.info(
                        f"The alert {id} skipped since it has been fetched before and maximum number of "
                        f"events per incident is reached"
                    )
                    continue

                filtered_alerts.append(alert)

    return filtered_alerts


def read_ids(siemplify, ids_file_name="ids.json"):
    """
    Read existing alerts IDs and related information from ids file (from last 24h only)
    :param siemplify: {Siemplify} Siemplify object.
    :param ids_file_name: {str} The name of the ids file
    :return: {dict} Alert ids and related information
    """
    ids_file_path = os.path.join(siemplify.run_folder, ids_file_name)

    if not os.path.exists(ids_file_path):
        return {}

    try:
        with open(ids_file_path, "r") as f:
            return json.loads(f.read())
    except Exception as e:
        siemplify.LOGGER.error(f"Unable to read ids file: {e}")
        siemplify.LOGGER.exception(e)
        return {}


def write_ids(siemplify, ids, ids_file_name="ids.json"):
    """
    Write ids and related information to the ids file
    :param siemplify: {Siemplify} Siemplify object.
    :param ids: {dict} The ids and related information to write to the file
    :param ids_file_name: {str} The name of the ids file.
    :return: {bool}
    """
    ids = {key: value for key, value in list(ids.items())[-STORED_IDS_LIMIT:]}

    try:
        ids_file_path = os.path.join(siemplify.run_folder, ids_file_name)

        if not os.path.exists(os.path.dirname(ids_file_path)):
            os.makedirs(os.path.dirname(ids_file_path))

        with open(ids_file_path, "w") as f:
            try:
                f.write(json.dumps(ids))
            except:
                # Move seeker to start of the file
                f.seek(0)
                # Empty the content of the file (the partially written content that was written before the exception)
                f.truncate()
                # Write an empty dict to the events data file
                f.write("{}")
                raise

        siemplify.LOGGER.info(f"Write ids. Total ids={len(ids.keys())}")
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


# Move to TIPCommon
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

    alerts = sorted(alerts, key=lambda alert: int(getattr(alert, timestamp_key)))
    last_timestamp = int(getattr(alerts[-1], timestamp_key)) + incrementation_value

    if log_timestamp:
        siemplify.LOGGER.info(f"Last timestamp is: {last_timestamp}")

    siemplify.save_timestamp(new_timestamp=last_timestamp)
    return True


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


def construct_alert_info(alert, existing_info=None):
    """
    Construct alert info containing ingested event ids and timestamp
    :param alert: {Alert} Alert object
    :param existing_info: {dict} Already existing info of the alert
    :return: {dict} Constructed alert info
    """
    return {
        "event_ids": list(
            set(
                (existing_info.get("event_ids") if existing_info else [])
                + [event.event_id for event in alert.events]
            )
        ),
        "first_seen": alert.incident_last_seen,
    }


def convert_hours_to_milliseconds(hours):
    """
    Convert hours to milliseconds
    :param hours: {int} hours to convert
    :return: {int} converted milliseconds
    """
    return hours * 60 * 60 * 1000


def xml_to_json(xml_string):
    """
    Convert xml string to json
    :param xml_string: {str} xml string to convert
    :return: {dict} converted json
    """
    return json.loads(json.dumps(xmltodict.parse(xml_string)))


def get_timestamps_from_range(range_string):
    """
    Get start and end time timestamps from range
    :param range_string: {str} Time range string
    :return: {tuple} start and end time timestamps
    """
    now = datetime.datetime.utcnow()
    today_datetime = datetime.datetime(
        year=now.year, month=now.month, day=now.day, hour=0, second=0
    )
    timeframe = TIMEFRAME_MAPPING.get(range_string)

    if isinstance(timeframe, dict):
        start_time, end_time = now - datetime.timedelta(**timeframe), now
    elif timeframe == TIMEFRAME_MAPPING.get("Last Week"):
        start_time, end_time = today_datetime + datetime.timedelta(
            -today_datetime.weekday(), weeks=-1
        ), today_datetime + datetime.timedelta(-today_datetime.weekday())

    elif timeframe == TIMEFRAME_MAPPING.get("Last Month"):
        end_time = today_datetime.today().replace(
            day=1, hour=0, minute=0, second=0
        ) - datetime.timedelta(days=1)
        start_time = today_datetime.today().replace(
            day=1, hour=0, minute=0, second=0
        ) - datetime.timedelta(days=end_time.day)
        end_time = end_time + datetime.timedelta(days=1)
    else:
        return None, None

    return start_time, end_time


def get_timestamps(range_string, start_time_string, end_time_string):
    """
    Get start and end time timestamps
    :param range_string: {str} Time range string
    :param start_time_string: {str} Start time
    :param end_time_string: {str} End time
    :return: {tuple} start and end time timestamps
    """
    start_time, end_time = get_timestamps_from_range(range_string)

    if not start_time and start_time_string:
        start_time = convert_timezone(
            convert_string_to_datetime(start_time_string), "UTC"
        )

    if not end_time and end_time_string:
        end_time = convert_timezone(convert_string_to_datetime(end_time_string), "UTC")

    if not start_time:
        raise Exception(
            '"Start Time" should be provided, when "Custom" is selected in "Time Frame" parameter.'
        )

    if not end_time:
        end_time = datetime.datetime.utcnow()

    start_time = int(convert_datetime_to_unix_time(start_time) / 1000)
    end_time = int(convert_datetime_to_unix_time(end_time) / 1000)

    return start_time, end_time
