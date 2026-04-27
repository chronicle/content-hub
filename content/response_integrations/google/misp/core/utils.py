from __future__ import annotations
from collections import defaultdict
import os
import requests
from soar_sdk.SiemplifyUtils import unix_now
from .constants import HASH_TYPES_WITH_LEN_MAPPING
import re
import tldextract
from .constants import EMAIL_PATTERN, EMAIL_TYPE, DOMAIN_PATTERN, DOMAIN_TYPE
from soar_sdk.SiemplifyDataModel import EntityTypes
import base64


UNIX_FORMAT = 1
DATETIME_FORMAT = 2
STORED_IDS_LIMIT = 1000


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


def clean_duplicated_keys(target_dict):
    """
    To fix duplicated keys issue.
    :param target_dict: {dict} dictionary to fix.
    :return: {dict} fixed dictionary.
    """
    result_dict = {}
    count_dict = defaultdict(int)
    for key in target_dict.keys():
        if key.lower() in result_dict:
            count_dict[key.lower()] += 1
            result_dict[f"{key.lower}_{count_dict.get(key.lower())}"] = target_dict.get(
                key
            )
        else:
            result_dict[key.lower()] = target_dict.get(key)

    return result_dict


def adjust_category_value(category):
    """
    Adjust category value
    :param category: {str} category value.
    :return: {str} adjusted value
    """
    return category.lower().capitalize()


def adjust_categories(category):
    """
    Adjust category value(s)
    :param category: {list or str} List of strings
    :return: {list} adjusted values or None
    """
    if isinstance(category, list):
        return list(map(adjust_category_value, category))
    elif isinstance(category, str):
        return adjust_category_value(category)


def string_to_multi_value(string_value, delimiter=","):
    """
    String to multi value.
    :param string_value: {str} String value to convert multi value.
    :param delimiter: {str} Delimiter to extract multi values from single value string.
    :return: {dict} fixed dictionary.
    """
    if not string_value:
        return []
    return [
        single_value.strip()
        for single_value in string_value.split(delimiter)
        if single_value.strip()
    ]


def get_entity_original_identifier(entity):
    """
    Helper function for getting entity original identifier
    :param entity: entity from which function will get original identifier
    :return: {str} original identifier
    """
    return entity.additional_properties.get("OriginalIdentifier", entity.identifier)


def get_entity_type(entity, extract_domain=False):
    """
    Helper function for getting entity type
    :param entity: entity from which function will get type
    :param extract_domain: extract_domain get domain from URL type entity or no
    :return: {str} entity type
    """
    if (
        re.search(EMAIL_PATTERN, get_entity_original_identifier(entity))
        and entity.entity_type == EntityTypes.USER
    ):
        return EMAIL_TYPE
    if (
        re.search(DOMAIN_PATTERN, get_entity_original_identifier(entity))
        and entity.entity_type == EntityTypes.URL
        and extract_domain
    ):
        return DOMAIN_TYPE

    return entity.entity_type


def get_domain_from_entity(identifier):
    """
    Extract domain from entity identifier
    :param identifier: {str} the identifier of the entity
    :return: {str} domain part from entity identifier
    """
    if "@" in identifier:
        return identifier.split("@", 1)[-1]
    try:
        result = tldextract.extract(identifier)
        if result.suffix:
            return ".".join([result.domain, result.suffix])
        return result.domain
    except ImportError:
        raise ImportError("tldextract is not installed. Use pip and install it.")


def get_hash_type(file_hash):
    """
    Helper function for getting file hash type
    :param file_hash: hash value
    :return: {str} hash type or None
    """
    if file_hash.count(":") == 2:
        return "ssdeep"

    return HASH_TYPES_WITH_LEN_MAPPING.get(len(file_hash))


def save_attachment(path, name, content):
    """
    Save attachment to local path
    :param path: {str} Path of the folder, where files should be saved
    :param name: {str} File name to be saved
    :param content: {str} File content
    :return: {str} Path to the downloaded files
    """
    # Create path if not exists
    if not os.path.exists(path):
        os.makedirs(path)
    # File local path
    local_path = os.path.join(path, name)
    with open(local_path, "wb") as file:
        file.write(base64.b64decode(content))
        file.close()

    return local_path
