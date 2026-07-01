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
from typing import NamedTuple

from datetime import datetime, timedelta

from TIPCommon.extraction import extract_configuration_param
from TIPCommon.types import ChronicleSOAR

from ..core.constants import INTEGRATION_NAME, TIMEFRAME_TO_HOURS, THREAT_STATUS_MAPPING
from ..core.datamodels import IntegrationParameters


class TimeInterval(NamedTuple):
    start_time: str
    end_time: str


def validate_positive_integer(number, err_msg="Limit parameter should be positive"):
    if number <= 0:
        raise Exception(err_msg)


def get_entity_original_identifier(entity):
    """
    Helper function for getting entity original identifier
    :param entity: entity from which function will get original identifier
    :return: {str} original identifier
    """
    return entity.additional_properties.get("OriginalIdentifier", entity.identifier)


def generate_time_intervals(
    start: datetime,
    end: datetime,
    hours: int,
) -> list[TimeInterval]:
    """Generates a list of 1-hour time intervals between a start and end datetime.

    Args:
        start (datetime): The start datetime.
        end (datetime): The end datetime.
        hours (int): The number of hours for each interval.

    Returns:
        list[TimeInterval]: A list of TimeInterval namedtuples, each representing a
        1-hour interval with start and end times in ISO 8601 format with 'Z'
        timezone indicator.
    """
    intervals = []
    while start < end:
        next_hour = min(start + timedelta(hours=hours), end)
        intervals.append(
            TimeInterval(
                f"{start.isoformat(timespec='seconds')}Z",
                f"{next_hour.isoformat(timespec='seconds')}Z",
            )
        )
        start = next_hour

    return intervals


def get_time_range(
    time_frame: str,
    custom_start: str | None = None,
    custom_end: str | None = None,
) -> tuple[datetime, datetime]:
    """
    Calculate the start and end times based on the provided time frame and custom
    start/end times.

    Args:
        time_frame (str): The time frame to search within (e.g., "Last Hour",
        "Last 6 Hours").
        custom_start (str, optional): Custom start time in ISO 8601 format.
        custom_end (str, optional): Custom end time in ISO 8601 format.

    Returns:
        tuple[datetime, datetime]: A tuple containing the start and end datetime
        objects.

    Raises:
        ValueError: If start time is after end time.
    """
    now = datetime.utcnow()
    if custom_start:
        start = datetime.fromisoformat(custom_start.replace("Z", ""))
        end = datetime.fromisoformat(custom_end.replace("Z", "")) if custom_end else now
    else:
        delta_hours = TIMEFRAME_TO_HOURS.get(time_frame, 1)
        end = now
        start = end - timedelta(hours=delta_hours)

    if start >= end:
        raise ValueError("Start time must be before end time")

    return start, end


def resolve_threat_statuses(threat_status: str) -> list[str]:
    if threat_status == "Select One":
        return ["active", "cleared"]

    return [THREAT_STATUS_MAPPING.get(threat_status)]


def get_integration_parameters(chronicle_soar: ChronicleSOAR) -> IntegrationParameters:
    """Get the parameters object for ProofPoint TAP auth and api manager
    Args:
        chronicle_soar (ChronicleSOAR): SiemplifyAction object.

    Returns:
        IntegrationParameters: IntegrationParameters object.
    """
    api_root: str = extract_configuration_param(
        chronicle_soar,
        provider_name=INTEGRATION_NAME,
        param_name="Api Root",
        is_mandatory=True,
        print_value=True,
    )
    username: str = extract_configuration_param(
        chronicle_soar,
        provider_name=INTEGRATION_NAME,
        param_name="Username",
        is_mandatory=True,
        print_value=True,
    )
    password: str = extract_configuration_param(
        chronicle_soar,
        provider_name=INTEGRATION_NAME,
        param_name="Password",
        is_mandatory=True,
    )
    verify_ssl: bool = extract_configuration_param(
        chronicle_soar,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        input_type=bool,
        print_value=True,
    )
    integration_params: IntegrationParameters = IntegrationParameters(
        api_root=api_root,
        username=username,
        password=password,
        verify_ssl=verify_ssl,
    )

    return integration_params
