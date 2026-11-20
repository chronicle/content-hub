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

import datetime
import hashlib
import itertools
import json
from typing import TYPE_CHECKING
import re
import requests

from soar_sdk.SiemplifyUtils import (
    convert_string_to_datetime,
    convert_timezone,
    utc_now,
    unix_now,
)
from TIPCommon.base.job.job_case import JobCase
from TIPCommon.consts import DATETIME_FORMAT, UNIX_FORMAT
from TIPCommon.data_models import AlertCard
from TIPCommon.smp_io import (
    read_ids,
    write_ids_with_timestamp,
    write_content,
    read_content,
)
from TIPCommon.types import SingleJson

from .constants import (
    ALERT_ID_KEY,
    ALERT_KEYS_DATETIME_SUFFIX,
    ALERT_UNIQUE_ID_HASH_SUFFIX_PATTERN,
    ALERT_UNIQUE_ID_KEY,
    SEVERITIES,
    TIMEFRAME_MAPPING,
    SEVERITY_MAP,
    M365_INCIDENT_ID_CONTEXT_KEY,
    ENTITY_TYPE,
)
from .Microsoft365DefenderExceptions import (
    APIPermissionError,
    Microsoft365DefenderException,
    NotEnoughEntitiesException,
    TooManyRequestsError,
    MissingSeverityFieldError,
    Microsoft365DefenderServerError,
)

if TYPE_CHECKING:
    from typing import Any

    from TIPCommon.types import ChronicleSOAR

EMAIL_REGEX = r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+"


def validate_response(response, error_msg="An error occurred"):
    """
    Validate response
    :param response: {requests.Response} The response to validate
    :param error_msg: {unicode} Default message to display on error
    """
    try:
        if response.status_code == 429:
            retry_after = response.headers.get("Retry-After")
            raise TooManyRequestsError(
                "Too many queries were executed. Rate limit is reached. ",
                retry_after=retry_after,
            )
        response.raise_for_status()

    except requests.HTTPError as error:

        if response.status_code == 403:
            raise APIPermissionError(f"{error_msg}: {error} {error.response.content}")

        if response.status_code == 500:
            raise Microsoft365DefenderServerError(
                "WARNING! Microsoft Defender API Service is down. "
                "Please try again in a minute."
            )

        try:
            response.json()
        except Exception:
            raise Microsoft365DefenderException(
                f"{error_msg}: {error} {error.response.content}"
            )

        api_error = response.json().get("error")
        error_message = (
            response.json().get("error", {}).get("message")
            if isinstance(api_error, dict)
            else response.json().get("error_description")
        )

        raise Microsoft365DefenderException(
            f"{error_msg}: {error} {error_message or response.content}"
        )


# Move to TIPCommon
def validate_end_time(end_time, time_format=DATETIME_FORMAT):
    """
    Validate end time interval
    :param end_time: {datetime} Last run timestamp + 12 hours interval
    :param time_format: {int} The format of the output time. Ex DATETIME, UNIX
    :return: {datetime} if end_time > current_time, return current time, else
    return end_time
    """
    current_time = unix_now() if time_format == UNIX_FORMAT else utc_now()
    if end_time > current_time:
        return current_time
    else:
        return end_time


def pass_severity_filter(siemplify, alert, lowest_severity, alert_type, parameter_name):
    """
    Check if alert passes severity filter

    Args:
        siemplify (SiemplifyConnectorExecution): SiemplifyConnectorExecution object
        alert (Incident | AlertWithEvidence): Alert to filter
        lowest_severity (str): Lowest severity to use for filtering
        alert_type (str): Alert type i.e. "Incident", "Alert"
        parameter_name (str): Name of the severity filter parameter

    Returns:
        bool: True if passes filter, False otherwise
    """
    # severity filter
    if lowest_severity:
        filtered_severities = (
            SEVERITIES[SEVERITIES.index(lowest_severity.lower()) :]
            if lowest_severity.lower() in SEVERITIES
            else []
        )
        if not filtered_severities:
            siemplify.LOGGER.error(
                f"Severity is not checked. Invalid value provided for "
                f'"{parameter_name}" parameter. Possible values are: '
                f"Informational, Low, Medium, High."
            )
        if filtered_severities and alert.severity.lower() not in filtered_severities:
            siemplify.LOGGER.info(
                f"{alert_type} with severity: {alert.severity} did not pass filter. "
                f"Lowest severity to fetch is {lowest_severity}."
            )
            return False
    return True


def get_timestamps_from_range(range_string):
    """
    Get start and end time timestamps from range
    :param range_string: {str} Time range string
    :return: {tuple} start and end time timestamps
    """
    now = datetime.datetime.utcnow()
    today_datetime = datetime.datetime(
        year=now.year, month=now.month, day=now.day, hour=0, second=0
    )
    timeframe = TIMEFRAME_MAPPING.get(range_string)

    if isinstance(timeframe, dict):
        start_time, end_time = now - datetime.timedelta(**timeframe), now
    elif timeframe == TIMEFRAME_MAPPING.get("Last Week"):
        start_time, end_time = (
            today_datetime + datetime.timedelta(-today_datetime.weekday(), weeks=-1),
            today_datetime + datetime.timedelta(-today_datetime.weekday()),
        )

    elif timeframe == TIMEFRAME_MAPPING.get("Last Month"):
        end_time = today_datetime.today().replace(
            day=1, hour=0, minute=0, second=0
        ) - datetime.timedelta(days=1)
        start_time = today_datetime.today().replace(
            day=1, hour=0, minute=0, second=0
        ) - datetime.timedelta(days=end_time.day)
        end_time = end_time + datetime.timedelta(days=1)
    else:
        return None, None

    return start_time, end_time


def get_timestamps(range_string, start_time_string, end_time_string):
    """
    Get start and end time timestamps
    :param range_string: {str} Time range string
    :param start_time_string: {str} Start time
    :param end_time_string: {str} End time
    :return: {tuple} start and end time timestamps
    """
    start_time, end_time = get_timestamps_from_range(range_string)

    if not start_time and start_time_string:
        start_time = convert_timezone(
            convert_string_to_datetime(start_time_string), "UTC"
        )

    if not end_time and end_time_string:
        end_time = convert_timezone(convert_string_to_datetime(end_time_string), "UTC")

    if not start_time:
        raise Exception(
            '"Start Time" should be provided, when "Custom" is selected'
            ' in "Time Frame" parameter.'
        )

    if not end_time:
        end_time = datetime.datetime.utcnow()

    return start_time.isoformat(), end_time.isoformat()


def convert_comma_separated_to_list(comma_separated):
    """
    Convert comma-separated string to list
    :param comma_separated: String with comma-separated values
    :return: List of values
    """
    return (
        [item.strip() for item in comma_separated.split(",")] if comma_separated else []
    )


def convert_list_to_comma_string(values_list):
    """
    Convert list to comma-separated string
    :param values_list: List of values
    :return: String with comma-separated values
    """
    return (
        ", ".join(str(v) for v in values_list)
        if values_list and isinstance(values_list, list)
        else values_list
    )


def check_if_key_provided(key, entities):
    """
    Checks whether the entity key for corresponding type is provided
    :param key: {str} Entity type key
    :param entities: {list} List of entity identifiers
    :return: True, exception otherwise
    """
    if key and not entities:
        raise NotEnoughEntitiesException(
            "Action wasn't able to build the query, because not enough entity types "
            'were supplied for the specified ".. Entity Keys". Please disable "Stop If '
            'Not Enough Entities" parameter or provide at least one entity for each '
            'specified ".. Entity Key".'
        )
    return True


def get_email_address(entity):
    """
    get email address
    :param entity: {entity}
    :return: email address if found, else None.
    """
    try:
        if "Email" in entity.additional_properties:
            return entity.additional_properties["Email"]
        else:
            if re.match(EMAIL_REGEX, entity.identifier, re.IGNORECASE):
                return entity.identifier
    except:
        pass


def read_existing_incidents(siemplify):
    """
    Proxy to existing read_ids from TipCommon, handles after migration data structure
    changes to ids.json file

    :param siemplify: {ConnectorExecutionInstance}
    :return: dict with incidents / alerts data {incident_id_1: [alert_id_1, alert_id_2]}
    """
    existing_ids = read_ids(siemplify, default_value_to_return={})
    if isinstance(existing_ids, list):
        return {}
    return existing_ids


def write_existing_incidents(
    siemplify,
    existing_incidents,
    fetched_incidents,
    limit_of_incidents,
    is_tracking_enabled=False,
):
    """
    Proxy to existing write_ids_with_timestamp from TipCommon, handles after migration
    data structure changes to ids.json file
    :param siemplify: {ConnectorExecutionInstance}
    :param existing_incidents: {Dict} existing incidents from prev iteration
    :param fetched_incidents: {List[Incident]} fetched incidents on current cycle
    :param limit_of_incidents: {int} Limit of incidents to store
    :param is_tracking_enabled: {bool} Specifies if alerts tracking is enabled
    :return: dict with incidents / alerts data {incident_id_1: [alert_id_1, alert_id_2]}
    """
    id_key = ALERT_UNIQUE_ID_KEY if is_tracking_enabled else ALERT_ID_KEY
    new_existing_incidents = {
        str(fetched_incident.incident_id): existing_incidents.get(
            str(fetched_incident.incident_id), []
        )
        + [getattr(alert, id_key, None) for alert in fetched_incident.alerts or []]
        for fetched_incident in fetched_incidents
    }
    existing_incidents = {
        key: value
        for key, value in existing_incidents.items()
        if key not in new_existing_incidents
    }

    if len(existing_incidents) + len(new_existing_incidents) > limit_of_incidents:
        # Ex: len(new_existing_incidents) -> 20, len(existing_incidents) -> 990,
        # limit_of_incidents -> 1000
        # Start for slice -> 990 - (1000 - 20) = 10, Stop -> None
        start_index = len(existing_incidents) - (
            limit_of_incidents - len(new_existing_incidents)
        )
        existing_incidents = dict(
            itertools.islice(existing_incidents.items(), start_index, None)
        )

    # Old 980 incidents + new 20 incidents -> 1000 incidents in total
    existing_incidents.update(new_existing_incidents)

    write_ids_with_timestamp(siemplify, existing_incidents)


def write_last_too_many_requests_occurrence(siemplify, encountered_at):
    """
    Save last occurrence of last TooManyRequests Error
    :param siemplify: {ConnectorExecutionInstance}
    :param encountered_at: {int} Encountered At in UNIX
    """
    if encountered_at is not None:
        siemplify.LOGGER.info(
            f"Writing last occurrence of TooManyRequests (429) error - "
            f"{datetime.datetime.fromtimestamp(encountered_at / 1000).isoformat()}"
        )

    write_content(
        siemplify,
        content_to_write=encountered_at,
        file_name="toomanyrequests_last_occurrence.txt",
        db_key="toomanyrequests_last_occurrence",
    )


def read_last_too_many_requests_occurrence(siemplify):
    """
    Save last occurrence of last TooManyRequests Error
    :param siemplify: {ConnectorExecutionInstance}
    :param encountered_at: {int} Encountered At in UNIX
    """
    encountered_at = (
        read_content(
            siemplify,
            file_name="toomanyrequests_last_occurrence.txt",
            db_key="toomanyrequests_last_occurrence",
        )
        or None
    )

    if encountered_at is not None:
        siemplify.LOGGER.info(
            f"Last occurrence of TooManyRequests (429) error - "
            f"{datetime.datetime.fromtimestamp(encountered_at / 1000).isoformat()}"
        )

    return encountered_at


def severity_to_priority(severity):
    """Maps Incident and alert severity values to SOAR priority values

    Args:
        severity (str): Defender 365 incident/alert severity

    Raises:
        MissingSeverityFieldError: if severity could not be determined

    Returns:
        int: SOAR priority value
    """
    if isinstance(severity, str):
        severity = severity.title()
    else:
        raise MissingSeverityFieldError(
            f"Severity field is not a string. Alert severity: {severity}, "
            f"type: {type(severity)}"
        )
    return SEVERITY_MAP.get(severity, -1)


def dict_to_md5_hash(
    dictionary: SingleJson,
    keys_to_ignore: list[str] | None = None,
) -> str:
    """Convert a dictionary to an MD5 hash string.

    Args:
        dictionary (SingleJson): Dictionary to convert to MD5 hash.
        keys_to_ignore (list[str] | None): List of keys to ignore.

    Returns:
        str: Converted MD5 hash string.
    """
    keys_to_ignore_lower = {k.lower() for k in (keys_to_ignore or [])}

    transformed_dictionary = {
        key: value for key, value in dictionary.items()
        if key.lower() not in keys_to_ignore_lower and ALERT_KEYS_DATETIME_SUFFIX not in key.lower()
    }

    return hashlib.md5(
        json.dumps(transformed_dictionary, sort_keys=True).encode()
    ).hexdigest()


def is_valid_m365_alert_id(alert_id: Any) -> bool:
    """Check if the provided alert ID is a valid string.

    Args:
        alert_id (Any): The alert ID to validate.

    Returns:
        bool: True if the alert ID is a valid string, False otherwise.
    """
    if not alert_id or isinstance(alert_id, int):
        return False

    return isinstance(alert_id, str)


def get_alert_id_from_display_id(display_id: str | None) -> str | None:
    """Extracts the original alert ID from a display ID.

    Args:
        display_id: The display ID of the alert.

    Returns:
        The original alert ID if found, otherwise None.
    """
    if not isinstance(display_id, str):
        return display_id

    return re.sub(ALERT_UNIQUE_ID_HASH_SUFFIX_PATTERN, "", display_id)


def get_m365_alert_id_from_soar_alert(
    soar_job: ChronicleSOAR,
    alert: AlertCard,
) -> str | None:
    """Get the Microsoft 365 Defender alert ID from a SOAR alert.

    Args:
        soar_job (ChronicleSOAR): The SOAR job object.
        alert (AlertCard): The SOAR alert object.

    Returns:
        str | None: The Microsoft 365 Defender alert ID if found, otherwise None.
    """
    valid_ticket_id: bool = (
        hasattr(alert, "ticket_id")
        and alert.ticket_id
        and str(alert.ticket_id).isdigit()
    )

    if valid_ticket_id:
        additional_properties: dict = json.loads(alert.additional_properties)
        display_id: str | None = additional_properties.get("DisplayId")
        if display_id:
            alert_id: str | None = get_alert_id_from_display_id(display_id)
            if is_valid_m365_alert_id(alert_id):
                return alert_id

    if hasattr(alert, "alert_group_identifier") and alert.alert_group_identifier:
        alert_id: str | None = soar_job.get_context_property(
            ENTITY_TYPE,
            alert.alert_group_identifier,
            M365_INCIDENT_ID_CONTEXT_KEY,
        )
        if is_valid_m365_alert_id(alert_id):
            return alert_id

    return None


def get_m365_alert_id_from_soar_alerts(
    soar_job: ChronicleSOAR,
    job_case: JobCase,
) -> dict[str, AlertCard]:
    """Get the Microsoft 365 Defender alert ID from a SOAR alert.

    Args:
        soar_job (ChronicleSOAR): The SOAR job object.
        job_case (JobCase): The SOAR job case object.

    Returns:
        dict[str, AlertCard]: A dictionary mapping Microsoft 365 Defender alert IDs
        to their corresponding SOAR alerts.
    """
    product_id_to_alert_mapping = {}
    for alert in job_case.case_detail.alerts:
        alert_id = get_m365_alert_id_from_soar_alert(soar_job, alert)
        if alert_id:
            product_id_to_alert_mapping[alert_id] = alert

    return product_id_to_alert_mapping

def parse_iso_datetime(value: str | None) -> datetime.datetime | None:
    if not value or not isinstance(value, str):
        return None
    return datetime.datetime.fromisoformat(value.replace("Z", "+00:00"))
