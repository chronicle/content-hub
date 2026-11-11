from __future__ import annotations
import json
import re
from typing import List

from google_cloud_iam.core.consts import SA_RESOURCE_NAME_PATTERN
from google_cloud_iam.core.exceptions import GoogleCloudIAMValidationError


def load_csv_to_list(csv: str, param_name: str) -> List[str]:
    """
    Load comma separated values represented as string to a list. Remove duplicates
    :param csv: {str} of comma separated values with delimiter ','
    :param param_name: {str} the name of the parameter we are loading csv to list
    :return: {[str]} List of separated string values
            raise GoogleCloudComputeValidationError if failed to parse csv string
    """
    try:
        return list(set([t.strip() for t in csv.split(",")]))
    except Exception as e:
        raise GoogleCloudIAMValidationError(
            f'Failed to load comma separated string parameter "{param_name}"'
        ) from e


def parse_string_to_dict(string):
    """
    Parse json string to dict
    :param string: string to parse
    :return: {dict} parsed dict
    """
    try:
        return json.loads(string)
    except Exception as e:
        raise GoogleCloudIAMValidationError(
            f"Unable to parse provided json. Error is: {e}"
        ) from e


def extract_service_account_resource_path(resource_name_str: str) -> (str, str):
    """Extract SA resource path from a given string by known PATTERN.

    Args:
        resource_name_str (str): String that contains instance resource path

    Raises:
        GoogleCloudIAMValidationError: If string does not contain the PATTERN

    Returns:
        tuple[str, str]: Tuple of SA project and SA identifier
    """
    resource_name_match = re.search(SA_RESOURCE_NAME_PATTERN, resource_name_str)
    if resource_name_match is None:
        raise GoogleCloudIAMValidationError(
            f"Given resource name string does not match expected pattern - "
            f"{SA_RESOURCE_NAME_PATTERN}"
        )

    return resource_name_match.group(1), resource_name_match.group(3)
