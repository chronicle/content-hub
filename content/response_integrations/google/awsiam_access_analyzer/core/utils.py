from __future__ import annotations
from .exceptions import AWSIAMValidationException


def remove_empty_kwargs(**kwargs):
    """
    Remove keys from dictionary that has the value None
    :param kwargs: key value arguments
    :return: dictionary without keys that have the value None
    """
    return {k: v for k, v in kwargs.items() if v is not None}


def load_csv_to_list(csv, param_name):
    """
    Load comma separated values represented as string to a list
    :param csv: {str} of comma separated values with delimiter ','
    :param param_name: {str} the name of the variable we are validation
    :return: {list} of values
            raise AWSIAMValidationException if failed to parse csv
    """
    try:
        return [t.strip() for t in csv.split(",")]
    except Exception:
        raise AWSIAMValidationException(f"Failed to parse parameter {param_name}")


def load_kv_csv_to_dict(kv_csv, param_name):
    """
    Load comma separated values of 'key':'value' represented as string to dictionary
    :param kv_csv: {str} of comma separated values of 'key':'value' represented as a string
    :param param_name: {str} name of the parameter
    :return: {dict} of key:value
            raise AWSIAMValidationException if failed to parse kv_csv
    """
    try:
        return {
            kv.split(":")[0].strip(): kv.split(":")[1].strip()
            for kv in kv_csv.split(",")
        }
    except Exception:
        raise AWSIAMValidationException(f"Failed to parse parameter {param_name}")
