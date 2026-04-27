from __future__ import annotations
import requests
import json
import os
import datetime
from .FortigateExceptions import FortigateException
from .constants import IP_SUBNET_CONVERSIONS, DEFAULT_IP_MASK, SUBNET_DELIMITER
from soar_sdk.SiemplifyUtils import utc_now, unix_now, convert_unixtime_to_datetime
from TIPCommon import validate_map_file
from EnvironmentCommon import EnvironmentHandle


# Move to TIPCommon
TIMEOUT_THRESHOLD = 0.9
WHITELIST_FILTER = 1
BLACKLIST_FILTER = 2
UNIX_FORMAT = 1
DATETIME_FORMAT = 2


def validate_response(response, sensitive_data_arr=None, error_msg="An error occurred"):
    """
    Validate response
    :param response: {requests.Response} The response to validate
    :param sensitive_data_arr: {list} The list of sensitive data
    :param error_msg: {str} Default message to display on error
    """
    try:
        response.raise_for_status()

    except requests.HTTPError as error:
        if sensitive_data_arr:
            raise FortigateException(
                encode_sensitive_data(
                    str(f"{error_msg}: {error} {error.response.content}"),
                    sensitive_data_arr,
                )
            )
        raise Exception(f"{error_msg}: {error} {error.response.content}")

    return True


def encode_sensitive_data(message, sensitive_data_arr):
    """
    Encode sensitive data
    :param message: {str} The error message which may contain sensitive data
    :param sensitive_data_arr: {list} The list of sensitive data
    :return: {str} The error message with encoded sensitive data
    """
    for sensitive_data in sensitive_data_arr:
        message = message.replace(sensitive_data, encode_data(sensitive_data))

    return message


def encode_data(sensitive_data):
    """
    Encode string
    :param sensitive_data: {str} String to be encoded
    :return: {str} Encoded string
    """
    if len(sensitive_data) > 1:
        return f"{sensitive_data[0]}...{sensitive_data[-1]}"

    return sensitive_data


def transform_ip_address(ip_address):
    """
    Transform ip addresses with subnet
    :param ip_address: {str} IP address
    :return: {str} Transformed IP address
    """
    if SUBNET_DELIMITER in ip_address:
        for key in reversed(list(IP_SUBNET_CONVERSIONS.keys())):
            if key in ip_address:
                return f"{ip_address.replace(key, '')} {IP_SUBNET_CONVERSIONS.get(key)}"
    else:
        return f"{ip_address} {DEFAULT_IP_MASK}"


def remove_subnet_from_ip_address(ip_address):
    """
    Remove subnet from ip addresses
    :param ip_address: {str} IP address
    :return: {str} Transformed IP address
    """
    if SUBNET_DELIMITER in ip_address:
        return ip_address[: ip_address.index(SUBNET_DELIMITER)]

    return ip_address


def get_domain_from_entity(identifier):
    """
    Extract domain from entity identifier
    :param identifier: {str} the identifier of the entity
    :return: {str} domain part from entity identifier
    """
    if "@" in identifier:
        return identifier.split("@", 1)[-1]
    try:
        import tldextract

        result = tldextract.extract(identifier)
        join_with = "."
        if result.suffix:
            if result.subdomain:
                return join_with.join([result.subdomain, result.domain, result.suffix])

            return join_with.join([result.domain, result.suffix])

        elif result.subdomain:
            return join_with.join([result.subdomain, result.domain])

        return result.domain

    except ImportError:
        raise ImportError("tldextract is not installed. Use pip and install it.")


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


def read_ids(siemplify, ids_file_name="ids.json"):
    """
    Read existing alerts IDs from ids file (from last 24h only)
    :param siemplify: {Siemplify} Siemplify object.
    :param ids_file_name: {str} The name of the ids file
    :return: {list} List of ids
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


def write_ids(siemplify, ids_json, total_ids_count, subtypes, ids_file_name="ids.json"):
    """
    Write ids to the ids file
    :param siemplify: {Siemplify} Siemplify object.
    :param ids_json: {dict} The ids to write to the file
    :param total_ids_count: {int} The ids count for subtype
    :param subtypes: {list} All of the subtypes in the scope
    :param ids_file_name: {str} The name of the ids file.
    :return: {bool}
    """
    try:
        if all(subtype in ids_json for subtype in subtypes):
            filtered_json = [
                subtype_json
                for subtype_name, subtype_json in ids_json.items()
                if subtype_name in subtypes
            ]
            if all(item.get("processed", False) for item in filtered_json):
                for subtype_json in ids_json.values():
                    subtype_json["processed"] = False

        ids_file_path = os.path.join(siemplify.run_folder, ids_file_name)

        if not os.path.exists(os.path.dirname(ids_file_path)):
            os.makedirs(os.path.dirname(ids_file_path))

        with open(ids_file_path, "w") as f:
            try:
                f.write(json.dumps(ids_json))
            except:
                f.write("{}")
                raise

        siemplify.LOGGER.info(f"Write ids. Total ids={total_ids_count}")
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


def get_last_success_time(
    siemplify, offset_with_metric, subtype, time_format=UNIX_FORMAT, print_value=True
):
    """
    Get last success time datetime
    :param siemplify: {siemplify} Siemplify object
    :param offset_with_metric: {dict} metric and value. Ex {"hours": 1}
    :param subtype: {str} The subtype to fetch timestamp for.
    :param time_format: {int} The format of the output time. Ex DATETIME, UNIX
    :param print_value: {bool} Whether log the value or not
    :return: {time} If first run, return current time minus offset time, else return timestamp from file
    """
    last_run_timestamp = fetch_timestamp_json(siemplify=siemplify).get(subtype, 0)

    offset = datetime.timedelta(**offset_with_metric)
    current_time = utc_now()
    offset_time_unix = int((current_time - offset).timestamp() * 1000000000)
    # Check if first run
    unix_result = (
        offset_time_unix
        if offset_time_unix > last_run_timestamp
        else last_run_timestamp
    )
    datetime_result = convert_unixtime_to_datetime(unix_result / 1000000)

    if print_value:
        siemplify.LOGGER.info(
            f"Last success time for subtype: {subtype}. "
            f"Date time:{datetime_result}. Unix:{unix_result}"
        )

    return unix_result if time_format == UNIX_FORMAT else datetime_result


def fetch_timestamp_json(siemplify, timestamp_file_name="timestamp.json"):
    timestamp_file_path = os.path.join(siemplify.run_folder, timestamp_file_name)

    if not os.path.exists(timestamp_file_path):
        return {}

    try:
        with open(timestamp_file_path, "r") as f:
            return json.loads(f.read())
    except Exception as e:
        siemplify.LOGGER.error(f"Unable to read timestamp file: {e}")
        siemplify.LOGGER.exception(e)
        return {}


def save_timestamp(
    siemplify,
    alerts,
    subtype,
    timestamp_key="timestamp",
    timestamp_file_name="timestamp.json",
    incrementation_value=0,
    log_timestamp=True,
):
    """
    Save last timestamp for given alerts
    :param siemplify: {Siemplify} Siemplify object
    :param alerts: {list} The list of alerts to find the last timestamp
    :param subtype: {str} The subtype to update timestamp for.
    :param timestamp_key: {str} key for getting timestamp from alert
    :param timestamp_file_name: {str} The name of the timestamp file.
    :param incrementation_value: {int} The value to increment last timestamp by milliseconds
    :param log_timestamp: {bool} Whether log timestamp or not
    :return: {bool} Is timestamp updated
    """
    if not alerts:
        siemplify.LOGGER.info(
            f'Timestamp for subtype "{subtype}" is not updated since no alerts fetched'
        )
        return False

    alerts = sorted(alerts, key=lambda alert: getattr(alert, timestamp_key))
    last_timestamp = getattr(alerts[-1], timestamp_key) + incrementation_value
    timestamp_json = fetch_timestamp_json(siemplify=siemplify)
    timestamp_json.update({subtype: last_timestamp})

    try:
        timestamp_file_path = os.path.join(siemplify.run_folder, timestamp_file_name)

        if not os.path.exists(os.path.dirname(timestamp_file_path)):
            os.makedirs(os.path.dirname(timestamp_file_path))

        with open(timestamp_file_path, "w") as f:
            try:
                f.write(json.dumps(timestamp_json))
            except:
                f.write("{}")
                raise

        if log_timestamp:
            siemplify.LOGGER.info(
                f'Last timestamp for subtype "{subtype}" is: {last_timestamp}'
            )
        return True

    except Exception as e:
        siemplify.LOGGER.error(
            f"Failed writing timestamp to timestamp file, ERROR: {e}"
        )
        siemplify.LOGGER.exception(e)
        return False


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


def convert_comma_separated_to_list(comma_separated):
    """
    Convert comma-separated string to list
    :param comma_separated: String with comma-separated values
    :return: List of values
    """
    return (
        [item.strip() for item in comma_separated.split(",")] if comma_separated else []
    )
