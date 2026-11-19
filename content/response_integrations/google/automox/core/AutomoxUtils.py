from __future__ import annotations
from automox.core.exceptions import AutomoxFilterException


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
