from __future__ import annotations
import os
import datetime
import arrow
import json
import requests
from soar_sdk.SiemplifyUtils import utc_now, convert_datetime_to_unix_time, unix_now
from EnvironmentCommon import EnvironmentHandle
from TIPCommon import validate_map_file

UNIX_FORMAT = 1
DATETIME_FORMAT = 2
STORED_IDS_LIMIT = 1000


# Move to TIPCommon
def get_last_success_time(
    siemplify, offset_with_metric, time_format=DATETIME_FORMAT, print_value=True
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
            f"Last success time. Date time:{datetime_result}. Unix:{unix_result}"
        )
    return unix_result if time_format == UNIX_FORMAT else datetime_result


def validate_response(response, error_msg="An error occurred"):
    """
    Validate response
    :param response: {requests.Response} The response to validate
    :param error_msg: {unicode} Default message to display on error
    """
    try:
        response.raise_for_status()

    except requests.HTTPError as error:
        raise Exception(f"{error_msg}: {error} {error.response.content}")

    return True


# Move to TIPCommon
def get_environment_common(
    siemplify, environment_field_name, environment_regex_pattern, map_file="map.json"
):
    """
    Get environment common
    :param siemplify: {siemplify} Siemplify object
    :param environment_field_name: {string} The environment field name
    :param environment_regex_pattern: {string} The environment regex pattern
    :param map_file: {string} The map file
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
def filter_old_alerts(logger, alerts, existing_ids, id_key="alert_id"):
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


# Move to TIPCommon
def read_ids(siemplify, ids_file_name="ids.json", max_hours_backwards=24):
    """
    Read existing (already seen) alert ids from the ids.json file
    :param max_hours_backwards: {int} Max amount of hours to keep ids in the file (to prevent it from getting too big)
    :param ids_file_name: {str} The name of the ids file
    :return:{dict} A dict describing the already seen ids {id: the unixtime when it was first seen}
    """
    ids_file_path = os.path.join(siemplify.run_folder, ids_file_name)
    siemplify.LOGGER.info(f"Fetching existing IDs from: {ids_file_path}")

    try:
        if not os.path.exists(ids_file_path):
            siemplify.LOGGER.info(f"Ids file doesn't exist at path {ids_file_path}")
            return {}

        with open(ids_file_path, "r") as f:
            siemplify.LOGGER.info("Reading existing ids from ids file")
            existing_ids = json.loads(f.read())

            filtered_ids = {}
            # Insert IDs that did not passed time retention time limit.
            for alert_id, timestamp in existing_ids.items():
                if (
                    timestamp
                    > arrow.utcnow().shift(hours=-max_hours_backwards).timestamp * 1000
                ):
                    filtered_ids[alert_id] = timestamp

            return filtered_ids

    except Exception as e:
        siemplify.LOGGER.error(f"Unable to read ids file: {e}")
        siemplify.LOGGER.exception(e)
        return {}


# Move to TIPCommon
def write_ids(siemplify, ids, ids_file_name="ids.json"):
    """
    Write ids to the ids file
    :param ids_file_name: {str} The name of the ids file
    :param ids: {dict} The ids to write to the file
    """
    try:
        ids_file_path = os.path.join(siemplify.run_folder, ids_file_name)
        siemplify.LOGGER.info(f"Writing ids to file: {ids_file_path}")

        if not os.path.exists(os.path.dirname(ids_file_path)):
            siemplify.LOGGER.info(
                f"Ids file doesn't exist at {ids_file_path}. Creating new file."
            )
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
                f.write("{}")
                raise

    except Exception as e:
        siemplify.LOGGER.error(f"Failed writing IDs to IDs file, ERROR: {e}")
        siemplify.LOGGER.exception(e)


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

    except Exception as err:
        siemplify.LOGGER.error(f"Error validation connector overflow, ERROR: {err}")
        siemplify.LOGGER.exception(err)
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
        siemplify.LOGGER.info(f"Saving timestamp:{last_timestamp}")

    siemplify.save_timestamp(new_timestamp=last_timestamp)
    return True


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
