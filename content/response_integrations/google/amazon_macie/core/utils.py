from __future__ import annotations
import json

from .exceptions import AmazonMacieValidationException


def remove_empty_kwargs(kwargs):
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
            raise AmazonMacieValidationException if failed to load filter json object string
                  to a dictionary
    """
    try:  # validate filter json object
        filter_json = json.loads(filter_json)
    except Exception:
        raise AmazonMacieValidationException("Failed to validate Filter JSON Object.")

    return filter_json


def get_mapped_value(mappings, key, default_value):
    """
    Returns mapped value of 'key' parameter. if default value is provided, and key equals default_value, None will be returned.
    otherwise, if key does not exist in mappings - an AWSGuardDutyValidationException will be thrown.

    :param mappings: {dict} of mapped keys to values
    :param key: {str} key to check if there is mapped value in mappings. if key is None, None will be returned.
    :param default_value: {str} used to prevent Exception throwing if key not in mappings
    :return: {str} value of key in mappings if key exists in mappings dictionary.
             None - if key=default_value or key is None
             otherwise if key exists in mappings the value will be returned {str}
             otherwise raise AmazonMacieValidationException
    """
    if not key or key == default_value:
        return None
    if key not in mappings:
        raise AmazonMacieValidationException(f"Failed to validate parameter {key}")
    return mappings.get(key)


def load_csv_to_list(csv, param_name):
    """
    Load comma separated values represented as string to a list
    :param csv: {str} of comma separated values with delimiter ','
    :param param_name: {str} the name of the variable we are validation
    :return: {list} of values
            raise AmazonMacieValidationException if failed to parse csv
    """
    try:
        return [t.strip() for t in csv.split(",")]
    except Exception:
        raise AmazonMacieValidationException(f"Failed to parse parameter {param_name}")


def load_kv_csv_to_dict(kv_csv, param_name):
    """
    Load comma separated values of 'key':'value' represented as string to dictionary
    :param kv_csv: {str} of comma separated values of 'key':'value' represented as a string
    :param param_name: {str} name of the parameter
    :return: {dict} of key:value
            raise AmazonMacieValidationException if failed to parse kv_csv
    """
    try:
        return {
            kv.split(":")[0].strip(): kv.split(":")[1].strip()
            for kv in kv_csv.split(",")
        }
    except Exception:
        raise AmazonMacieValidationException(f"Failed to parse parameter {param_name}")
