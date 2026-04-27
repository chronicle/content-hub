from __future__ import annotations
from .exceptions import AWSCloudTrailValidationException


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
    :param csv: {str} of comma seperated values with delimiter ','
    :param param_name: {str} the name of the variable we are validation
    :return: {list} of values
            raise AWSCloudTrailValidationException if failed to parse csv
    """
    try:
        return [t.strip() for t in csv.split(",")]
    except Exception as error:
        raise AWSCloudTrailValidationException(
            f"Failed to parse parameter {param_name}"
        ) from error
