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

from typing import Any
import datetime
import requests

UNIX_FORMAT = 1
DATETIME_FORMAT = 2
STORED_IDS_LIMIT = 3000


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


def get_earliest_event_at_datetime(alerts):
    """
    Get event_at datetime from earliest alert in alert list
    :param alerts: The alerts list
    :return: {str} The earliest event_at
    """
    alerts.sort(key=lambda alert: datetime.datetime.strptime(alert.get("event_at"), "%Y-%m-%dT%H:%M:%S.%fZ"))
    return alerts[0].get("event_at")


def convert_comma_separated_to_list(comma_separated):
    """
    Convert comma-separated string to list
    :param comma_separated: String with comma-separated values
    :return: List of values
    """
    return [item.strip() for item in comma_separated.split(",")] if comma_separated else []


def convert_list_to_comma_string(values_list):
    """
    Convert list to comma-separated string
    :param values_list: List of values
    :return: String with comma-separated values
    """
    return ", ".join(str(v) for v in values_list) if values_list and isinstance(values_list, list) else values_list


def parse_bulk_acquisition_id(bulk_id: Any) -> int:
    """Validate and parse a bulk acquisition ID into an integer.

    Args:
        bulk_id: Raw bulk acquisition ID.

    Returns:
        Validated integer bulk acquisition ID.

    Raises:
        ValueError: If the ID is empty or cannot be parsed as a numeric integer.
    """
    if not bulk_id or not str(bulk_id).strip():
        raise ValueError("Bulk Acquisition ID must not be empty.")

    try:
        return int(str(bulk_id).strip())
    except ValueError as value_error:
        raise ValueError(f"Bulk Acquisition ID must be a number, got: {bulk_id}.") from value_error
