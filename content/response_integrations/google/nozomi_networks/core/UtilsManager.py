from __future__ import annotations
import os
import datetime
import json
import requests
from soar_sdk.SiemplifyUtils import utc_now, unix_now
from EnvironmentCommon import EnvironmentHandle
from TIPCommon import validate_map_file

from .NozomiNetworksConstants import (
    LIMIT_IDS_IN_IDS_FILE,
    TIMEOUT_THRESHOLD,
    ALERT_ID_FIELD,
    IDS_FILE,
    MAP_FILE,
)


def validate_response(response, error_msg="An error occurred"):
    """
    Validate response
    :param response: {requests.Response} The response to validate
    :param error_msg: {str} Default message to display on error
    """
    try:
        response.raise_for_status()

    except requests.HTTPError as error:
        raise Exception(f"{error_msg}: {error} {error.response.content}")

    return True


def is_approaching_timeout(connector_starting_time, python_process_timeout):
    """
    Check if a timeout is approaching.
    :param connector_starting_time: {int} Connector start time
    :param python_process_timeout: {int} The python process timeout
    :return: {bool} True if timeout is close, False otherwise
    """
    processing_time_ms = unix_now() - connector_starting_time
    return processing_time_ms > python_process_timeout * 1000 * TIMEOUT_THRESHOLD


def validate_timestamp(last_run_timestamp, offset_in_hours):
    """
    Validate timestamp in range
    :param last_run_timestamp: {datetime} last run timestamp
    :param offset_in_hours: {int} backward hours count
    :return: {datetime} if first run, return current time minus offset time, else return timestamp from file
    """
    current_time = utc_now()
    # Check if first run
    if current_time - last_run_timestamp > datetime.timedelta(hours=offset_in_hours):
        return current_time - datetime.timedelta(hours=offset_in_hours)
    else:
        return last_run_timestamp


# Move to TIPCommon
def get_environment_common(
    siemplify, environment_field_name, environment_regex_pattern, map_file=MAP_FILE
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
def filter_old_alerts(logger, alerts, existing_ids, id_key=ALERT_ID_FIELD):
    """
    Filter alerts that were already processed
    :param logger: {SiemplifyLogger} Siemplify logger
    :param alerts: {list} The alerts to filter
    :param existing_ids: {list} The ids to filter
    :param id_key: {str} The key of identifier
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
def read_ids(siemplify, ids_file_name=IDS_FILE):
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
def write_ids(siemplify, ids, ids_file_name=IDS_FILE):
    """
    Write ids to the ids file
    :param siemplify: {Siemplify} Siemplify object.
    :param ids: {list} The ids to write to the file
    :param ids_file_name: {str} The name of the ids file.
    :return: {bool}
    """
    ids = ids[-LIMIT_IDS_IN_IDS_FILE:]
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
    except Exception as err:
        siemplify.LOGGER.error(f"Failed writing IDs to IDs file, ERROR: {str(err)}")
        siemplify.LOGGER.exception(err)
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

    except Exception as err:
        siemplify.LOGGER.error(f"Error validation connector overflow, ERROR: {err}")
        siemplify.LOGGER.exception(err)
        if is_test_run:
            raise

    return False
