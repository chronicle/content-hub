# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import annotations
import copy

from typing import Any

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


def prevent_reverting_properties(entity: Any) -> None:
    """Monkeypatches the `to_dict` method on the given entity object to prevent
    reverting read-only properties (IsPivot, IsAttacker, IsVulnerable) to False/False string.

    This is necessary because the SecOps SOAR platform does not allow changing these
    properties from True to False, resulting in a 400 Bad Request error.

    Args:
        entity: The DomainEntityInfo (or similar) entity object.
    """
    if not hasattr(entity, "to_dict"):
        return

    add_props = getattr(entity, "additional_properties", {}) or {}

    is_pivot = (
        getattr(entity, "is_pivot", False)
        or str(add_props.get("IsPivot", "")).lower() == "true"
    )
    is_attacker = (
        getattr(entity, "is_attacker", False)
        or getattr(entity, "attacker", False)
        or str(add_props.get("IsAttacker", "")).lower() == "true"
    )
    is_vulnerable = (
        getattr(entity, "is_vulnerable", False)
        or str(add_props.get("IsVulnerable", "")).lower() == "true"
    )

    if not (is_pivot or is_attacker or is_vulnerable):
        return

    orig_to_dict = entity.to_dict

    def new_to_dict():
        d = orig_to_dict().copy()
        d.pop("to_dict", None)

        def clean_key(target_dict, key):
            target_dict.pop(key, None)

        if is_pivot:
            clean_key(d, "is_pivot")
            clean_key(d, "IsPivot")
        if is_attacker:
            clean_key(d, "is_attacker")
            clean_key(d, "attacker")
            clean_key(d, "IsAttacker")
        if is_vulnerable:
            clean_key(d, "is_vulnerable")
            clean_key(d, "IsVulnerable")

        add_props_dict = d.get("additional_properties") or d.get("additionalProperties")
        if isinstance(add_props_dict, dict):
            add_props_dict = add_props_dict.copy()
            if is_pivot:
                clean_key(add_props_dict, "IsPivot")
            if is_attacker:
                clean_key(add_props_dict, "IsAttacker")
            if is_vulnerable:
                clean_key(add_props_dict, "IsVulnerable")

            if "additional_properties" in d:
                d["additional_properties"] = add_props_dict
            if "additionalProperties" in d:
                d["additionalProperties"] = add_props_dict

        return d

    entity.to_dict = new_to_dict
