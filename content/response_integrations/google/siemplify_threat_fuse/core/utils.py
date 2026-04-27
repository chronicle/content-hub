from __future__ import annotations
import datetime
import json
import os
import re

from EnvironmentCommon import EnvironmentHandle
from TIPCommon import validate_map_file
from . import consts
from soar_sdk.SiemplifyUtils import convert_datetime_to_unix_time, utc_now, unix_now
from .exceptions import ThreatFuseValidationException

UNIX_FORMAT = 1
DATETIME_FORMAT = 2


def get_search_association_types(association_types: dict) -> [str]:
    """
    Return list of mapped association types. Association type 'Observables' will be last in list.
    :param association_types: {dict} Keys are unmapped search association type, Values are True Or False
    :return: {[str]} list of mapped association types, for association_types which values are True
    """
    types = [
        consts.ASSOCIATIONS_TYPES.get(key)
        for key, value in association_types.items()
        if value
    ]
    observables_type = consts.ASSOCIATIONS_TYPES.get("Observables")
    if observables_type in types:
        observables_type_idx = types.index(observables_type)
        types[observables_type_idx], types[-1] = types[-1], types[observables_type_idx]
    return types


def get_max_dict_value_size(dict: dict) -> int:
    """
    Return the maximum length of a value in a dictionary
    :param dict: {dict} dictionary. Values should be iterables not string
    :return: {int} maximum length of a value in a dictionary
    """
    return max([len(value) for value in dict.values()]) if dict else 0


def convert_dict_values_from_set_to_list(dict: dict) -> dict:
    """
    Return dictionary with key values as list, instead of set
    :param dict: {dict} with key values of type set.
    :return: {dict} dictionary with key values of type list.
    """
    return {k: list(v) for k, v in dict.items()}


def get_last_modified(cve_obj):
    id_modified_time_list = [
        {"id": x["id"], "modified_ts": x["modified_ts"]} for x in cve_obj.objects
    ]
    id_modified_time_list = sorted(
        id_modified_time_list, key=lambda k: k["modified_ts"]
    )
    return id_modified_time_list[-1].get("id", None)


def convert_string_to_unix_time(time_str: str):
    """
    Convert string time of format 2020-03-15T04:24:55.428496 or 2020-03-15T04:24:55.428496Z to unix time in ms
    :param time_str: {str} time in format '2020-03-15T04:24:55.428496' or '2020-03-15T04:24:55.428496Z'
    :return: {int} unix time in ms
    """
    try:
        dt = datetime.datetime.strptime(time_str, consts.TIME_FORMAT)
        return convert_datetime_to_unix_time(dt)
    except Exception as e:
        pass

    try:
        dt = datetime.datetime.strptime(time_str, consts.OBSERVABLE_TIME_FORMAT)
        return convert_datetime_to_unix_time(dt)
    except Exception as e:
        pass
    return 1


def datetime_to_string(datatime_obj: datetime.datetime) -> str:
    """
    Convert datetime object to 2020-03-15T04:24:55.428496 time format
    :param datatime_obj: {datetime.datetime} The datetime object to convert
    :return: {str} The string representation of the datetime in format 2020-03-15T04:24:55.428496
    """
    return datatime_obj.strftime(consts.TIME_FORMAT)


def load_csv_to_list(csv: str, param_name: str):
    """
    Load comma separated values represented as string to a list
    :param csv: {str} of comma separated values
    :param param_name: {str} the name of the variable we are validation
    :return: {list} of values
            raise ThreatFuseValidationException if failed to parse csv
    """
    try:
        return [t.strip() for t in csv.split(",")]
    except Exception:
        raise ThreatFuseValidationException(f"Failed to parse parameter {param_name}")


def load_valid_csv_to_list(csv: str, param_name: str, valid_params: list) -> list:
    """
    Load comma separated values represented as string to a list, each value must exist in <valid_params> list
    :param csv: {str} of comma separated values
    :param param_name: {str} the name of the variable we are validation
    :param valid_params: {list} list of valid parameters of comma separated values
    :return: {list} of values
            raise ThreatFuseValidationException if failed to parse csv or one of the values is not valid
    """
    try:
        splitted = []  # splitted values
        for v in csv.split(","):
            if v.strip() not in valid_params:
                raise ThreatFuseValidationException(
                    f"Value {v} in comma-separated list {param_name} found to be invalid. Valid values are {', '.join(valid_params)}"
                )
            splitted.append(v.strip())
        return splitted
    except ThreatFuseValidationException as e:
        raise e
    except Exception:
        raise ThreatFuseValidationException(f"Failed to parse parameter {param_name}")


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
def read_ids(siemplify, ids_file_name):
    """
    Read all existing alerts IDs from ids file
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
def write_ids(siemplify, ids, ids_file_name, limit_ids_in_ids_file):
    """
    Write ids to the ids file. Writes latest 'limit_ids_in_ids_file' param ids in ids json file
    :param siemplify: {Siemplify} Siemplify object.
    :param ids: {list} The ids to write to the file
    :param ids_file_name: {str} The name of the ids file.
    :param limit_ids_in_ids_file: {int} max ids to write in ids json file
    :return: {bool}
    """
    ids = ids[-limit_ids_in_ids_file:]
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


def get_entity_original_identifier(entity):
    """
    helper function for getting entity original identifier
    :param entity: entity from which function will get original identifier
    :return: {str} original identifier
    """
    return entity.additional_properties.get("OriginalIdentifier", entity.identifier)


def convert_formatted_string_to_unix_time(time_str: str, date_format: str):
    """
    Convert string time of format <date_format> to unix time in ms
    :param time_str: {str} time in <date_format> format
    :param date_format: {str} date format of time string
    :return: {int} unix time in ms
    """
    dt = datetime.datetime.strptime(time_str, date_format)
    return convert_datetime_to_unix_time(dt)


def is_valid_email(user_name: str) -> bool:
    """
    Check if the user_name is valid email.
    :param user_name: {str} User name
    :return: {bool} True if valid email, else False
    """
    return bool(re.search(consts.VALID_EMAIL_REGEXP, user_name))


def as_html_link(link: str) -> str:
    return f"""<a href="{link}" target="_blank">{link}</a>"""


def convert_datetime_to_string(datetime_obj: datetime.datetime):
    """
    Convert datetime object to string of format 2020-03-15T04:24:55.428496
    :param datetime_obj: {datetime.datetime} datetime object
    :return: {str} of date in format 2020-03-15T04:24:55.428496
    """
    return datetime_obj.strftime(consts.TIME_FORMAT)


def slice_list_to_max_sublists(data: list, max_size_sublist: int):
    """
    Slice list into sublists. Each sublist will have max size of <max_size_sublist>
    :param data: {[]} list of values to split to sublists
    :param max_size_sublist: {int} max size of sublist
    :return: {[[]]} list of sublists of max size <max_size_sublist>
    """
    return [
        data[x : x + max_size_sublist] for x in range(0, len(data), max_size_sublist)
    ]


def append_association_type_to_entities(
    entities: list, mapper: dict, type: str, entity_identifier: str
):
    """
    Append entity object to entities list. Mapper maps supported entities to True
    :param entities: {list} list of entities to append the new entity object
    :param mapper: {dict} maps the type to bool. If True the type is supported
    :param type: {str} the type of the mapped value
    :param entity_identifier: {str} the identifier of the entity to append
    :return: {list} list of updated entities
    """
    if mapper.get(type):
        entities.append(
            {
                "identifier": entity_identifier,
                "type": consts.ASSOCIATION_TYPE_TO_ENTITY.get(type),
            }
        )
    return entities
