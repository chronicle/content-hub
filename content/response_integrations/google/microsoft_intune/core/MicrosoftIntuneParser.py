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

from .datamodels import Device, GetManageDeviceData, ListManagedDevices


def build_get_managed_device_obj(raw_data: dict) -> GetManageDeviceData:
    """
    Builds Get Manage Device dataclass

    Args:
        raw_data: Raw API data item

    Returns:
        Filled Get Manage Device object
    """
    return GetManageDeviceData(raw_data)


def build_list_managed_devices_obj(raw_data: dict) -> ListManagedDevices:
    """
    Builds List Managed Devices dataclass

    Args:
        raw_data: Raw API data item

    Returns:
        Filled List Manage Devices object
    """
    return ListManagedDevices(
        raw_data=raw_data,
        devices=[build_list_device_object(item) for item in raw_data.get("value")],
        count=raw_data.get("@odata.count"),
    )


def build_list_all_managed_devices_obj(raw_data: dict) -> ListManagedDevices:
    """
    Builds List Managed Devices dataclass

    Args:
        raw_data: Raw API data item

    Returns:
        Filled List Manage Devices object
    """
    return ListManagedDevices(
        raw_data=raw_data,
        devices=[build_list_device_object(item) for item in raw_data.get("value")],
        count=raw_data.get("@odata.count"),
    )


def build_list_device_object(item_data: dict) -> Device:
    """
    Builds List Managed Device dataclass

    Args:
        item_data: Raw API data item

    Returns:
        Filled List Manage Device object
    """
    return Device(
        item_data=item_data,
        device_id=item_data.get("id"),
        user_id=item_data.get("userId"),
        device_name=item_data.get("deviceName"),
        operating_system=item_data.get("operatingSystem"),
        compliance_state=item_data.get("complianceState"),
        enrolled_date=item_data.get("enrolledDateTime"),
        last_sync_date=item_data.get("lastSyncDateTime"),
    )


def extract_error_message(error_json: dict) -> str:
    default_error_msg = "Error message is not available"
    msgs = error_json.get("messages")
    if msgs and isinstance(msgs, list):
        return msgs[0].get("text", default_error_msg)

    msg = error_json.get("message")
    if msg and isinstance(msg, str):
        return msg

    return default_error_msg
