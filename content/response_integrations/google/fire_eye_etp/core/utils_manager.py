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


"""Utility functions for FireEye ETP integration."""

from __future__ import annotations

import datetime

import requests
from dateutil import parser
from dateutil.tz import tzoffset

from .fire_eye_etp_exceptions import FireEyeETPError


def naive_time_converted_to_aware(time_param: str, timezone_offset: str) -> datetime.datetime:
    """Convert naive time string to aware datetime object.

    Args:
        time_param: Naive time string to convert.
        timezone_offset: UTC timezone offset string (e.g. "2" or "-5").

    Returns:
        The timezone-aware datetime object.

    """
    parsed_date = parser.parse(time_param)
    return datetime.datetime(
        parsed_date.year,
        parsed_date.month,
        parsed_date.day,
        parsed_date.hour,
        parsed_date.minute,
        parsed_date.second,
        tzinfo=get_server_tzoffset(timezone_offset),
    )


def get_server_tzoffset(server_timezone: str) -> tzoffset:
    """Get server timezone offset from UTC.

    Args:
        server_timezone: UTC timezone offset string (e.g. "2" or "-5").

    Returns:
        The tzoffset object.

    """
    return tzoffset(None, float(server_timezone) * 60 * 60)


def current_server_time(timezone_offset: str) -> datetime.datetime:
    """Get the current server time with timezone offset.

    Args:
        timezone_offset: UTC timezone offset string.

    Returns:
        The current time as a timezone-aware datetime object.

    """
    return datetime.datetime.now(tz=get_server_tzoffset(timezone_offset))


def validate_response(response: requests.Response, error_msg: str = "An error occurred") -> bool:
    """Validate HTTP response and raise FireEyeETPError on failure.

    Args:
        response: The response to validate.
        error_msg: Default message to display on error.

    Returns:
        True if response is successful.

    Raises:
        FireEyeETPError: If the response status code indicates an error.

    """
    try:
        response.raise_for_status()
    except requests.HTTPError as error:
        # Assign to variable first to satisfy ruff's EM102 rule
        msg = f"{error_msg}: {error} {error.response.content}"
        raise FireEyeETPError(msg) from error

    return True


def validate_timestamp(
    last_run_timestamp: datetime.datetime,
    offset_in_hours: int,
    current_time: datetime.datetime,
) -> datetime.datetime:
    """Validate timestamp is within the allowed range.

    Args:
        last_run_timestamp: The last run timestamp.
        offset_in_hours: The allowed offset in hours.
        current_time: The current server time.

    Returns:
        The validated timestamp (either last_run_timestamp or current_time minus offset).

    """
    # Check if first run
    if current_time - last_run_timestamp > datetime.timedelta(hours=offset_in_hours):
        return current_time - datetime.timedelta(hours=offset_in_hours)
    return last_run_timestamp
