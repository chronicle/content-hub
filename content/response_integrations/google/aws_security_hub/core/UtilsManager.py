from __future__ import annotations
import json

from .exceptions import AWSSecurityHubValidationException

UNIX_FORMAT = 1
DATETIME_FORMAT = 2
STORED_IDS_LIMIT = 1000


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
        alert_id = getattr(alert, id_key)
        if alert_id not in existing_ids:
            filtered_alerts.append(alert)
        else:
            logger.info(
                f"The alert {alert_id} skipped since it has been fetched before"
            )

    return filtered_alerts


def remove_empty_kwargs(**kwargs):
    """
    Remove keys from dictionary that has the value None
    :param kwargs: key value arguments
    :return: dictionary without keys that have the value None
    """
    return {k: v for k, v in kwargs.items() if v is not None}


def validate_filter_json_object(filter_json):
    """
    Loads filter json object string to a dictionary.
    :param filter_json: {str} of filter json object
    :return: {dict} of filter_json
            raise AWSSecurityHubValidationException if failed to load filter json object string
                  to a dictionary
    """
    try:  # validate filter json object
        filter_json = json.loads(filter_json)
    except Exception as error:
        raise AWSSecurityHubValidationException(
            "Failed to validate Filter JSON Object."
        ) from error

    return filter_json


def get_mapped_value(mappings, key, default_value):
    """
    Returns mapped value of 'key' parameter.
    If default value is provided, and key equals default_value, None will be returned.
    otherwise, if key does not exist in mappings - an AWSSecurityHubValidationException will be thrown.

    :param mappings: {dict} of mapped keys to values
    :param key: {str} key to check if there is mapped value in mappings. if key is None, None will be returned
    :param default_value: {str} used to prevent Exception throwing if key not in mappings
    :return: {str} value of key in mappings if key exists in mappings dictionary.
             None - if key=default_value or key is None
             otherwise if key exists in mappings the value will be returned {str}
             otherwise raise AWSSecurityHubValidationException
    """
    if not key or key == default_value:
        return None
    if key not in mappings:
        raise AWSSecurityHubValidationException(f"Failed to validate parameter {key}")
    return mappings.get(key)


def load_csv_to_list(csv, param_name):
    """
    Load comma separated values represented as string to a list
    :param csv: {str} of comma seperated values with delimiter ','
    :param param_name: {str} the name of the variable we are validation
    :return: {list} of values
            raise AWSSecurityHubValidationException if failed to parse csv
    """
    try:
        return [t.strip() for t in csv.split(",")]
    except Exception as error:
        raise AWSSecurityHubValidationException(
            f"Failed to parse parameter {param_name}"
        ) from error


def load_kv_csv_to_dict(kv_csv, param_name):
    """
    Load comma separated values of 'key':'value' represented as string to dictionary
    :param kv_csv: {str} of comma separated values of 'key':'value' represented as a string
    :param param_name: {str} name of the parameter
    :return: {dict} of key:value
            raise AWSSecurityHubValidationException if failed to parse kv_csv
    """
    try:
        return {
            kv.split(":")[0].strip(): kv.split(":")[1].strip()
            for kv in kv_csv.split(",")
        }
    except Exception as error:
        raise AWSSecurityHubValidationException(
            f"Failed to parse parameter {param_name}"
        ) from error
