from __future__ import annotations
import os
import datetime
import json
from soar_sdk.SiemplifyUtils import utc_now, convert_datetime_to_unix_time, unix_now
from EnvironmentCommon import EnvironmentHandle, validate_map_file_exists

from .constants import (
    UNIX_FORMAT,
    DATETIME_FORMAT,
    SYNC_SECURITY_INCIDENTS_JSON,
    SYNC_FIELDS,
    SECURITY_INCIDENTS_FIELD,
)


STORED_IDS_LIMIT = 6000
TIMEOUT_THRESHOLD = 0.9


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
    :param ids_file_name: {unicode} The name of the ids file.
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
    except Exception as err:
        siemplify.LOGGER.error(f"Failed writing IDs to IDs file, ERROR: {err}")
        siemplify.LOGGER.exception(err)
        return False


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
    :param environment_field_name: {string} The environment field name
    :param environment_regex_pattern: {string} The environment regex pattern
    :param map_file: {string} The map file
    :return: {EnvironmentHandle}
    """
    map_file_path = os.path.join(siemplify.run_folder, map_file)
    validate_map_file_exists(map_file_path, siemplify.LOGGER)
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
            alert_identifier=str(alert_info.ticket_id),
            alert_name=str(alert_info.rule_generator),
            product=str(alert_info.device_product),
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
        siemplify.LOGGER.info(f"Last timestamp is :{last_timestamp}")

    siemplify.save_timestamp(new_timestamp=last_timestamp)
    return True


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


def get_list_item_by_index(data, index):
    """
    Get list item by index
    :param data: {list} The list
    :param index: {int} The index
    :return: The list item
    """
    try:
        return data[index]
    except IndexError:
        return None


def write_configs(siemplify, configs, file_name="config.json"):
    """
    Write configs to the config file
    :param siemplify: {Siemplify} Siemplify object
    :param configs: {dict} The configs to write to the file
    :param file_name: {unicode} The name of the configs file
    :return: {bool}
    """
    try:
        file_path = os.path.join(siemplify.run_folder, file_name)

        if not os.path.exists(os.path.dirname(file_path)):
            os.makedirs(os.path.dirname(file_path))

        with open(file_path, "w") as f:
            try:
                for chunk in json.JSONEncoder().iterencode(configs):
                    f.write(chunk)
            except:
                # Move seeker to start of the file
                f.seek(0)
                # Empty the content of the file (the partially written content that was written before the exception)
                f.truncate()
                # Write an empty dict
                f.write("{}")
                raise

        siemplify.LOGGER.info(
            "The application configurations are written in config file"
        )
        return True

    except Exception as err:
        siemplify.LOGGER.error(
            f"Failed writing configurations to config file, ERROR: {err}"
        )
        siemplify.LOGGER.exception(err)
        return False


def read_configs(siemplify, file_name="config.json"):
    """
    Read configs from config file
    :param siemplify: {Siemplify} Siemplify object.
    :param file_name: {str} The name of the configs file
    :return: {dict} The dict of configs
    """
    file_path = os.path.join(siemplify.run_folder, file_name)

    if not os.path.exists(file_path):
        return {}

    try:
        with open(file_path, "r") as f:
            return json.loads(f.read())
    except Exception as e:
        siemplify.LOGGER.error(f"Unable to read config file: {e}")
        siemplify.LOGGER.exception(e)
        return {}


def get_case_and_ticket_ids(case):
    """
    Extract incident case ticket ids
    :param case: cases object
    :return: {dict} Dict of {case id, ticket id}
    """
    case_alert_ids = {}
    for alert in case.get("cyber_alerts", []):
        case_id, ticket_id = case.get("identifier"), alert.get(
            "additional_properties", {}
        ).get("TicketId")
        if not ticket_id:
            continue
        if not case_alert_ids.get(case_id):
            case_alert_ids[case_id] = ""
        case_alert_ids[case_id] = ticket_id
    return case_alert_ids


def write_sync_data(siemplify, sync_data, file_name=SYNC_SECURITY_INCIDENTS_JSON):
    """
    Write sync data to the sync security incidents file
    :param siemplify: {Siemplify} Siemplify object
    :param sync_data: {dict} The sync data to write to the file
    :param file_name: {str} The name of the configs file
    :return: {bool}
    """
    try:
        file_path = os.path.join(siemplify.run_folder, file_name)

        if not os.path.exists(os.path.dirname(file_path)):
            os.makedirs(os.path.dirname(file_path))

        with open(file_path, "w") as f:
            try:
                for chunk in json.JSONEncoder().iterencode(sync_data):
                    f.write(chunk)
            except:
                # Move seeker to start of the file
                f.seek(0)
                # Empty the content of the file (the partially written content that was written before the exception)
                f.truncate()
                # Write an empty dict
                f.write("{}")
                raise

        siemplify.LOGGER.info("The sync data is written in the file")
        return True

    except Exception as err:
        siemplify.LOGGER.error(
            f"Failed writing sync data to sync security incidents file, ERROR: {err}"
        )
        siemplify.LOGGER.exception(err)
        return False


def read_sync_data(siemplify, file_name=SYNC_SECURITY_INCIDENTS_JSON):
    """
    Read sync data from sync security incidents file
    :param siemplify: {Siemplify} Siemplify object.
    :param file_name: {str} The name of the sync security incidents file
    :return: {dict} The dict of sync data
    """
    file_path = os.path.join(siemplify.run_folder, file_name)

    if not os.path.exists(file_path):
        return {SYNC_FIELDS: [], SECURITY_INCIDENTS_FIELD: []}

    try:
        with open(file_path, "r") as f:
            return json.loads(f.read())
    except Exception as e:
        siemplify.LOGGER.error(f"Unable to read sync security incidents file: {e}")
        siemplify.LOGGER.exception(e)
        return {}
