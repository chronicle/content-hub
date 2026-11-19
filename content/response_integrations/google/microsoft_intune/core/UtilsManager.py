from __future__ import annotations

from collections import Counter

from microsoft_intune.core.constants import (
    FILTER_KEY_DEFAULT_VALUE,
    FILTER_LOGIC_CONTAINS,
    FILTER_LOGIC_DEFAULT_VALUE,
    FILTER_LOGIC_EQUAL,
    FILTER_VALUE_DEFAULT_VALUE,
)
from microsoft_intune.core.datamodels import Device


def get_entity_original_identifier(entity) -> str:
    """
    Get entity original identifier.

    Args:
        entity: An entity from which function will get original identifier.

    Returns:
        An original identifier.
    """
    return entity.additional_properties.get("OriginalIdentifier", entity.identifier)


def is_valid_host(devices: list[Device], host: str, is_host_id: bool) -> bool:
    """
    Verify device in MS Intune

    Args:
        devices: List of devices
        host: Host should be host id or host name
        is_host_id: Flag to check it is host id or host name

    Returns:
        bool
    """
    if is_host_id:
        return any(host == device.device_id for device in devices)
    else:
        return any(host.casefold() == device.host_name.casefold() for device in devices)


def get_valid_host_id_by_name(devices: list[Device], host_name: str) -> str:
    """
    Get valid host id from host name

    Args:
        devices: device list
        host_name: Host name for get host id

    Returns:
        str
    """
    return next(
        (
            device.device_id
            for device in sorted_devices_by_last_date_time(devices)
            if host_name.casefold() == device.host_name.casefold()
        ),
        None,
    )


def sorted_devices_by_last_date_time(devices: list[Device]) -> list[Device]:
    """
    Sort Device list by Last date time key

    Args:
        devices: device list

    Returns:
        list
    """
    sorted_devices = sorted(devices, key=lambda x: x.last_sync_date, reverse=True)
    return sorted_devices


def check_multiple_host_id_exists(devices: list[Device], host_name: str) -> bool:
    """
    Verify multiple intune agents

    Args:
        devices: device list
        host_name: host name

    Returns:
        bool
    """
    host_name_counts = Counter(
        device.host_name.casefold()
        for device in sorted_devices_by_last_date_time(devices)
        if host_name.casefold() == device.host_name.casefold()
    )
    return any(count > 1 for count in host_name_counts.values())


def filter_list_data(
    response: list,
    filter_key: str = FILTER_KEY_DEFAULT_VALUE,
    filter_logic: str = FILTER_LOGIC_DEFAULT_VALUE,
    filter_value: str = FILTER_VALUE_DEFAULT_VALUE,
) -> list:
    """
    Filtering List Managed Devices Based on Keys

    Args:
        response: Raw API data
        filter_key: Key used to filter the list of managed devices.
        filter_logic:
           The logic determining how the filtering should be applied,
           such as 'equal', 'contains', etc.
        filter_value:
            The value to look for in the specified key as per the filter logic.

    Returns:
        list of managed devices
    """

    def handling_encoding(value: str, encode=True) -> str:
        return value.encode("utf-8") if encode else value.encode().decode("utf-8")

    def is_string_utf8(item: str) -> bool:
        return any(ord(char) > 127 for char in item)

    if filter_key == FILTER_KEY_DEFAULT_VALUE or not filter_value:
        return response

    if is_string_utf8(filter_value):
        filter_value = handling_encoding(filter_value, encode=False)

    filtered_value = [
        item
        for item in response
        if (
            filter_logic == FILTER_LOGIC_EQUAL
            and filter_value == str(item[filter_key].encode().decode("utf-8"))
        )
        or (
            filter_logic == FILTER_LOGIC_CONTAINS
            and filter_value in str(item[filter_key].encode().decode("utf-8"))
        )
        or (
            filter_logic == FILTER_LOGIC_DEFAULT_VALUE
            and filter_value in str(item[filter_key].encode().decode("utf-8"))
        )
    ]

    return filtered_value
