from __future__ import annotations
import datetime
import json
import os
from typing import Union

from EnvironmentCommon import EnvironmentHandle
from TIPCommon import validate_map_file

from soar_sdk.SiemplifyUtils import utc_now, convert_datetime_to_unix_time, unix_now
from .consts import UNIX_FORMAT, TIME_FORMAT

STORED_IDS_LIMIT = 1000
TIMEOUT_THRESHOLD = 0.9


def load_csv_to_list(csv: str, param_name: str) -> list:
    """
    Load comma separated values represented as string to a list
    :param csv: {str} of comma separated values
    :param param_name: {str} the name of the variable we are validation
    :return: {list} of values
            raise Exception if failed to load csv to list
    """
    try:
        return [v.strip() for v in csv.split(",")]
    except Exception:
        raise Exception(f'Failed to load parameter "{param_name}"')


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

        siemplify.LOGGER.info(f"Write ids. Total ids = {len(ids)}")
        return True

    except Exception as e:
        siemplify.LOGGER.error(f"Failed writing IDs to IDs file, ERROR: {e}")
        siemplify.LOGGER.exception(e)
        return False


# Move to TIPCommon
def get_last_success_time(
    siemplify, offset_with_metric, time_format=UNIX_FORMAT, print_value=True
):
    """
    Get last success time datetime
    :param siemplify: {siemplify} Siemplify object
    :param offset_with_metric: {dict} metric and value. Ex {'hours': 1}
    :param time_format: {int} The format of the output time. Ex DATETIME, UNIX
    :param print_value: {bool} Whether log the value or not
    :return: {time} If first run, return current time minus offset time, else return timestamp from file
    """
    last_run_timestamp = siemplify.fetch_timestamp(datetime_format=True)
    offset = datetime.timedelta(**offset_with_metric)
    current_time = utc_now()
    # Check if first run
    datetime_result = (
        current_time - offset
        if current_time - last_run_timestamp > offset
        else last_run_timestamp
    )
    unix_result = convert_datetime_to_unix_time(datetime_result)

    if print_value:
        siemplify.LOGGER.info(
            f"Last success time. Date time: {datetime_result}. Unix: {unix_result}"
        )

    return unix_result if time_format == UNIX_FORMAT else datetime_result


def is_approaching_timeout(connector_starting_time, python_process_timeout):
    """
    Check if a timeout is approaching.
    :param connector_starting_time: {int} Connector start time
    :param python_process_timeout: {int} The python process timeout
    :return: {bool} True if timeout is close, False otherwise
    """
    processing_time_ms = unix_now() - connector_starting_time
    return processing_time_ms > python_process_timeout * 1000 * TIMEOUT_THRESHOLD


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


# Move to TIPCommon
def filter_old_alerts(logger, alerts, existing_ids, id_key="alert_id"):
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


def convert_datetime_str_to_timestamp(datetime_str: str) -> (Union[int, str], bool):
    """
    Convert datetime string represented in format "YYYY-MM-DDThh:mm:ssZ" to unix timestamp in seconds
    :param datetime_str: {str} Datetime to convert to unix timestamp
    :return: {({int or str},{bool}) Tuple of unix timestamp in seconds representing the datetime if succeeded to convert, and status
    if succeeded to convert to timestamp in seconds or not. If failed to convert, original parameter will be returned
        raise Exception if failed to validate datetime of format "YYYY-MM-DDThh:mm:ssZ"
    """
    try:
        timestamp = convert_datetime_to_unix_time(
            datetime.datetime.strptime(datetime_str, TIME_FORMAT)
        )
        return timestamp, True
    except Exception:
        return datetime_str, False


def convert_string_timestamp_to_integer(timestamp: str) -> (Union[int, str], bool):
    """
    Convert string unix timestamp in seconds to integer.
    :param timestamp: {str} Unix timestamp to be converted to integer
    :return: {({int or str},{bool})} Tuple of unix timestamp as integer if succeeded to convert and status if conversion succeeded. If
    conversion failed, original parameter will be returned
    """
    try:
        int_timestamp = int(timestamp)
        return int_timestamp, True
    except Exception:
        return timestamp, False


def validate_date_parameter(date_parameter: str, parameter_name: str) -> int:
    """
    Check if date parameter is of format "YYYY-MM-DDThh:mm:ss" or unix timestamp "1611938799000"
    and convert to unix timestamp of type integer
    :param date_parameter: {str} Date parameter of format "YYYY-MM-DDThh:mm:ss" or "1611938799000"
    :param parameter_name: {str} Parameter name
    :return: {int} Converted unix time
        raise LogPointInvalidParametersException if failed to validate date parameter
    """
    # Check if start time is of format "YYYY-MM-DDThh:mm:ss"
    date_parameter, conversion_succeeded = convert_datetime_str_to_timestamp(
        date_parameter
    )
    if not conversion_succeeded:
        # Check if start time is of unix timestamp
        date_parameter, conversion_succeeded = convert_string_timestamp_to_integer(
            date_parameter
        )
        if not conversion_succeeded:
            raise Exception(f'Failed to validate "{parameter_name}" date parameter')

    return date_parameter
