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
from base64 import b64encode
import datetime
from datetime import timezone
import os
from typing import Iterable, List, Any, NoReturn

import requests

from soar_sdk.SiemplifyDataModel import Attachment
from soar_sdk.SiemplifyUtils import convert_string_to_datetime

from TIPCommon.extraction import extract_configuration_param
from TIPCommon.types import ChronicleSOAR

from ..core.constants import (
    TIMEFRAME_MAPPING,
    SEVERITIES,
    INTEGRATION_NAME,
)
from ..core.datamodels import IntegrationParameters
from ..core.MimecastExceptions import MimecastException


def lazy_chunk_iterable(
    iterable_to_chunk: List[Any], chunk_size: int
) -> Iterable[List[Any]]:
    for i in range(0, len(iterable_to_chunk), chunk_size):
        yield iterable_to_chunk[i : i + chunk_size]


def _handle_fail_string(fail: str, error_msg: str) -> NoReturn:
    raise MimecastException(f"{error_msg}: {fail}")


def _handle_fail_dict(fail: dict, error_msg: str) -> NoReturn:
    errors = fail.get("errors", [])
    error_messages = [
        error.get("message", "") for error in errors if error.get("message")
    ]
    if error_messages:
        raise MimecastException(f"{error_msg}: {', '.join(error_messages)}")

    if fail.get("message"):
        raise MimecastException(f"{error_msg}: {fail['message']}")


def _handle_fail_list(fail: list, error_msg: str) -> NoReturn:
    if not fail:
        return

    first_fail = fail[0]
    if isinstance(first_fail, dict):
        errors = first_fail.get("errors", []) if first_fail else []
        error_messages = [
            error.get("message", "") for error in errors if error.get("message")
        ]
        if error_messages:
            raise MimecastException(f"{error_msg}: {', '.join(error_messages)}")


def validate_response(
    response: requests.Response,
    error_msg: str = "An error occurred",
) -> None:
    """Validate response from Mimecast API.

    Args:
        response (requests.Response): The response to validate
        error_msg (str): Default message to display on error

    Raises:
        MimecastException: If the response indicates an error or is invalid
    """
    try:
        response.raise_for_status()

        try:
            data = response.json()
        except requests.JSONDecodeError as exc:
            if not response.content:
                raise MimecastException(
                    f"{error_msg}: Empty response received."
                ) from exc
            return

        fail = data.get("fail")
        if not fail:
            return

        if isinstance(fail, str):
            _handle_fail_string(fail, error_msg)

        if isinstance(fail, dict):
            _handle_fail_dict(fail, error_msg)

        if isinstance(fail, list) and fail:
            _handle_fail_list(fail, error_msg)

        raise MimecastException(f"{error_msg}: Unknown error in response.")

    except requests.HTTPError as error:
        raise MimecastException(
            f"{error_msg}: {error} {error.response.content}"
        ) from error


def pass_severity_filter(siemplify, alert, lowest_severity, ingest_without_risk):
    # severity filter
    if lowest_severity:
        filtered_severities = (
            SEVERITIES[SEVERITIES.index(lowest_severity.lower()) :]
            if lowest_severity.lower() in SEVERITIES
            else []
        )
        if not filtered_severities:
            siemplify.LOGGER.info(
                f'Risk is not checked. Invalid value provided for "Lowest Risk To Fetch" '
                f"parameter. Possible values are: Negligible, Low, Medium, High."
            )
        else:
            if alert.message_details.risk:
                if alert.message_details.risk.lower() not in filtered_severities:
                    siemplify.LOGGER.info(
                        f"Message with risk: {alert.message_details.risk} did not pass filter. "
                        f"Lowest risk to fetch is {lowest_severity}."
                    )
                    return False
            else:
                if not ingest_without_risk:
                    siemplify.LOGGER.info(
                        f"Message without risk did not pass filter. "
                        f'"Ingest Messages Without Risk" parameter is unchecked.'
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
        start_time, end_time = today_datetime + datetime.timedelta(
            -today_datetime.weekday(), weeks=-1
        ), today_datetime + datetime.timedelta(-today_datetime.weekday())

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
        start_time = convert_string_to_datetime(start_time_string)

    if not end_time and end_time_string:
        end_time = convert_string_to_datetime(end_time_string)

    if not start_time:
        raise Exception(
            '"Start Time" should be provided, when "Custom" is selected in "Time Frame" parameter.'
        )

    if not end_time:
        end_time = datetime.datetime.utcnow().replace(tzinfo=timezone.utc)

    if start_time > end_time:
        raise Exception('"End Time" should be later than "Start Time"')

    return start_time.isoformat(), end_time.isoformat()


def filter_message(messages, subject, sender):
    """Filters a list of messages by subject and sender.

    Args:
        messages (list): List of message dictionaries.
        subject (str): Subject to filter by.
        sender (str): Sender to filter by.

    Returns:
        dict or None: Matching message, or None if not found.
    """
    if len(messages) == 1:
        return messages[0]
    for message in messages:
        if message.subject == subject and message.sender == sender:
            return message
    return None


def get_integration_parameters(siemplify: ChronicleSOAR) -> IntegrationParameters:
    """
    Get integration parameters

    Args:
        siemplify (ChronicleSOAR): ChronicleSOAR object.
    """
    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Root",
        is_mandatory=True,
        print_value=True,
    )
    app_id = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Application ID",
        print_value=True,
    )
    app_key = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Application Key",
        remove_whitespaces=False,
    )
    access_key = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Access Key",
        remove_whitespaces=False,
    )
    secret_key = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Secret Key",
        remove_whitespaces=False,
    )
    client_id = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Client ID",
        print_value=True,
    )
    client_secret = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Client Secret",
        remove_whitespaces=False,
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        input_type=bool,
        is_mandatory=True,
        print_value=True,
    )

    integration_parameters = IntegrationParameters(
        app_id=app_id,
        api_root=api_root,
        app_key=app_key,
        access_key=access_key,
        secret_key=secret_key,
        client_id=client_id,
        client_secret=client_secret,
        verify_ssl=verify_ssl,
    )

    return integration_parameters


def create_siemplify_case_wall_attachment_object(
    full_file_name: str,
    file_contents: bytes,
) -> Attachment:
    """Creates a Siemplify case wall attachment object from file contents.

    This function takes a file name and its binary contents, converts the contents
    to base64, and creates a Siemplify Attachment object suitable for adding to
    the case wall.

    Args:
        full_file_name (str): Complete filename including extension
            (e.g. "document.pdf")
        file_contents (bytes): Raw binary contents of the file

    Returns:
        Attachment: A Siemplify Attachment object.
    """
    base64_blob = b64encode(file_contents).decode()

    file_name, file_extension = os.path.splitext(full_file_name)
    attachment_object = Attachment(
        case_identifier=None,
        alert_identifier=None,
        base64_blob=base64_blob,
        attachment_type=file_extension,
        name=file_name,
        description="Original email attachment",
        is_favorite=False,
        orig_size=len(file_contents),
        size=len(base64_blob),
    )

    return attachment_object
