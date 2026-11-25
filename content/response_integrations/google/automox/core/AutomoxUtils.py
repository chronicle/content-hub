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
from .exceptions import AutomoxFilterException


def filter_policies(policies, filter_key=None, filter_logic=None, filter_value=None):
    if not all((filter_key, filter_logic, filter_value)):
        return policies

    if filter_logic == "Contains":
        return [
            policy
            for policy in policies
            if filter_value in str(policy.raw_data.get(filter_key, ""))
        ]
    elif filter_logic == "Equal":
        return [
            policy
            for policy in policies
            if filter_value == str(policy.raw_data.get(filter_key, ""))
        ]
    else:
        raise AutomoxFilterException(f"Invalid filter logic: {filter_logic}")


def filter_devices_by_field(devices, filter_field, filter_value):
    if not all((filter_field, filter_value)):
        return devices

    filtered_devices = []
    for device in devices:
        target_field = getattr(device, filter_field)
        if isinstance(target_field, list) and filter_value in target_field:
            filtered_devices.append(device)
        elif target_field == filter_value:
            filtered_devices.append(device)
    return filtered_devices


def get_entity_original_identifier(entity):
    """
    Helper function for getting entity original identifier
    :param entity: entity from which function will get original identifier
    :return: {str} original identifier
    """
    return entity.additional_properties.get("OriginalIdentifier", entity.identifier)


def filter_patches(patches):
    """
    Helper function for filtering patches by installed and ignored
    :param patches: list of patches
    :return: {list} filtered patches
    """
    return [patch for patch in patches if not patch.ignored and not patch.installed]
