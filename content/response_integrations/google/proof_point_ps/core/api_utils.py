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

from datetime import UTC, datetime, timedelta

import requests

from .exceptions import InvalidParameterError, ProofPointPSHTTPError


def validate_response(
    response: requests.Response, error_msg: str = "An error occurred"
) -> None:
    """Validate HTTP response and raise custom exceptions.

    Args:
        response: The requests.Response to validate.
        error_msg: The custom error message prefix.

    Raises:
        ProofPointPSHTTPError: If the request failed.

    """
    try:
        response.raise_for_status()
    except requests.HTTPError as error:
        msg = f"{error_msg}: {error} - {response.content.decode('utf-8')}"
        raise ProofPointPSHTTPError(msg) from error


def parse_iso8601_to_utc_datetime(time_str: str) -> datetime:
    """Parse ISO8601 string into a UTC naive datetime.

    Args:
        time_str: The datetime string to parse.

    Returns:
        A datetime object in UTC timezone without tzinfo.

    Raises:
        ValueError: If the string cannot be parsed.

    """
    time_str = time_str.strip()
    if time_str.endswith("Z"):
        time_str = time_str[:-1] + "+00:00"

    try:
        datetime_obj = datetime.fromisoformat(time_str)
    except ValueError as exc:
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
            try:
                datetime_obj = datetime.strptime(time_str, fmt)
                break
            except ValueError:
                continue
        else:
            msg = f"Invalid datetime format: {time_str}"
            raise ValueError(msg) from exc

    if datetime_obj.tzinfo is not None:
        datetime_obj = datetime_obj.astimezone(UTC).replace(tzinfo=None)
    return datetime_obj


def calculate_time_range(
    time_frame: str,
    start_time_str: str | None = None,
    end_time_str: str | None = None,
) -> tuple[datetime, datetime]:
    """Calculate start/end datetimes based on timeframe and custom range.

    Args:
        time_frame: The lookback period choice.
        start_time_str: Custom start time string.
        end_time_str: Custom end time string.

    Returns:
        A tuple of start and end naive UTC datetime objects.

    Raises:
        InvalidParameterError: If the parameters are invalid.

    """
    now = datetime.now(UTC)

    if time_frame == "Custom":
        if not start_time_str:
            msg = "Start Time is required when Time Frame is set to 'Custom'."
            raise InvalidParameterError(msg)

        try:
            start = parse_iso8601_to_utc_datetime(start_time_str)
        except ValueError as e:
            msg = f"Invalid 'Start Time' format: {e}"
            raise InvalidParameterError(msg) from e

        if end_time_str:
            try:
                end = parse_iso8601_to_utc_datetime(end_time_str)
            except ValueError as e:
                msg = f"Invalid 'End Time' format: {e}"
                raise InvalidParameterError(msg) from e
        else:
            end = now

        if start.tzinfo is not None:
            start = start.astimezone(UTC).replace(tzinfo=None)
        if end.tzinfo is not None:
            end = end.astimezone(UTC).replace(tzinfo=None)

        if start >= end:
            msg = "Start Time must be before End Time."
            raise InvalidParameterError(msg)

        return start, end

    if start_time_str or end_time_str:
        msg = (
            "Start Time or End Time can only be provided when 'Custom' is "
            "selected for the Time Frame parameter."
        )
        raise InvalidParameterError(msg)

    delta_map = {
        "Last Hour": timedelta(hours=1),
        "Last 6 Hours": timedelta(hours=6),
        "Last 24 Hours": timedelta(hours=24),
        "Last Week": timedelta(days=7),
    }
    delta = delta_map.get(time_frame)
    if not delta:
        msg = f"Unsupported Time Frame: {time_frame}"
        raise InvalidParameterError(msg)

    end = now
    start = end - delta

    start = start.replace(tzinfo=None)
    end = end.replace(tzinfo=None)
    return start, end

