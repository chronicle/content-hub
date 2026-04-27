from __future__ import annotations
import copy

from .ActiveDirectoryManager import ActiveDirectoryManagerError
from soar_sdk.SiemplifyUtils import unix_now


def load_csv_to_list(csv: str, param_name: str):
    """
    Load comma separated values represented as string to a list. Remove duplicates if exist
    :param csv: {str} of comma separated values with delimiter ','
    :param param_name: {str} the name of the parameter we are loading csv to list
    :return: {[str]} List of separated string values
            raise TruSTARValidationException if failed to parse csv string
    """
    try:
        return list(set([t.strip() for t in csv.split(",")]))
    except Exception:
        raise ActiveDirectoryManagerError(
            f'Failed to load comma separated string parameter "{param_name}"'
        )


def get_existing_fields_to_enrich(fields_to_enrich, existing_fields):
    """
    Get fields to enrich the entity according to a provided list of fields
    :param fields_to_enrich: {list} The provided list of fields.
    :param existing_fields: {list} existing model fields.
    :return {({str}, {str})} Set of field to enrich the entity with, Set of existing attributes
    """
    existing_fields_to_enrich = set()
    existing_attributes = set()

    for field in fields_to_enrich:
        for existing_field in existing_fields:
            existing_field_splitted = existing_field.split("_")
            if field in existing_field_splitted:
                existing_fields_to_enrich.add(existing_field)
                existing_attributes.add(field)

    return existing_fields_to_enrich, existing_attributes


def filter_nested_dictionary(nested_dictionary, keys):
    """
    Returns filtered dictionary that will contains only dictionaries and lists that contains the keys provided.
    For example: for the nested dictionary: {'a': 1, 'b': 2, 'c': 3, 'd': {'a': 3, 'b': 5, 'g': ['o', {'a': 10}, 'a', {'c': {'a': 'd'}}]}}
    for the list of keys ['a'] the method will return: {'a': 1, 'd': {'a': 3, 'g': [{'a': 10}, {'c': {'a': 'd'}}]}}.
    :param nested_dictionary: {dict} Dictionary tha may contain nested dictionaries and lists.
    :param keys: {list} list of keys to keep from the original dictionary.
    :return: {dict} Filtered dictionary according to the provided keys.
    """
    if isinstance(nested_dictionary, dict):
        retVal = {}
        for key in nested_dictionary:
            if key in keys:
                retVal[key] = copy.deepcopy(nested_dictionary[key])
            elif isinstance(nested_dictionary[key], list) or isinstance(
                nested_dictionary[key], dict
            ):
                child = filter_nested_dictionary(nested_dictionary[key], keys)
                if child:
                    retVal[key] = child
        if retVal:
            return retVal
        else:
            return None
    elif isinstance(nested_dictionary, list):
        retVal = []
        for entry in nested_dictionary:
            child = filter_nested_dictionary(entry, keys)
            if child:
                retVal.append(child)
        if retVal:
            return retVal
        else:
            return None


ASYNC_ACTION_TIMEOUT_THRESHOLD_MS = 35 * 1000  # 35 seconds
ASYNC_ACTION_ITERATION_TIMEOUT_MS = 5 * 60 * 1000  # 5 minutes
ASYNC_ACTION_ITERATION_TIMEOUT_THRESHOLD_MS = 1 * 60 * 1000  # 1 minute


def is_action_approaching_timeout(python_process_timeout):
    """
    Check if a action script timeout is approaching.
    :param python_process_timeout: {int} The python process timeout
    :return: {bool} True if timeout is close, False otherwise
    """
    return unix_now() >= python_process_timeout - ASYNC_ACTION_TIMEOUT_THRESHOLD_MS


def is_action_approaching_iteration_run_timeout(action_start_time):
    """
    Check if action iteration run timeout approaching
    :param action_start_time: {int} timeout in milliseconds
    :return: {bool} True - if timeout is approaching, False - otherwise.
    """
    return (
        unix_now()
        >= action_start_time
        + ASYNC_ACTION_ITERATION_TIMEOUT_MS
        - ASYNC_ACTION_ITERATION_TIMEOUT_THRESHOLD_MS
    )
