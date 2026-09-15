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

import json
from urllib.parse import urljoin

import requests

from azure_monitor.core.constants import ENDPOINTS
from azure_monitor.core.exceptions import (
    AzureMonitorHTTPError,
    InvalidCredsError,
    InvalidRequestParametersError,
)


def get_full_url(
    api_root: str,
    endpoint_id: str,
    endpoints: dict[str, str] = None,
    **kwargs,
) -> str:
    """Construct the full URL using a URL identifier and optional variables

    Args:
        api_root (str): The root of the API endpoint
        endpoint_id (str): The identifier for the specific URL
        endpoints (dict[str, str]): endpoints dictionary object
        kwargs (dict): Variables passed for string formatting

    Returns:
        str: The full URL constructed from API root, endpoint identifier and variables

    """
    endpoints = endpoints or ENDPOINTS
    return urljoin(api_root, endpoints[endpoint_id].format(**kwargs))


def validate_response(
    response: requests.Response,
    error_msg: str = "An error occurred",
) -> None:
    """
    Validate an HTTP response and raise custom exceptions with detailed messages.

    Args:
        response (requests.Response): The HTTP response to validate.
        error_msg (str): Default message prefix to include in raised errors.

    Raises:
        InvalidRequestParametersError: For 400, 403, or 404 HTTP status codes.
        AzureMonitorHTTPError: For all other HTTP errors.
    """
    try:
        response.raise_for_status()
        return

    except requests.HTTPError as error:
        status = response.status_code

        try:
            error_json = response.json()
            error_info = error_json.get("error", {})
            inner_error = error_info.get("innererror", {})

            message = (
                inner_error.get("innererror", {}).get("message")
                or inner_error.get("message")
                or error_info.get("message")
                or response.text
                or "Unknown error"
            )
        except (json.JSONDecodeError, KeyError, AttributeError):
            message = response.text or "Unknown error"

        if "error_description" in error_json:
            raise InvalidCredsError("Please Check your Credentials.") from error

        if status in (400, 403, 404):
            raise InvalidRequestParametersError(message) from error

        raise AzureMonitorHTTPError(
            f"{error_msg}: {message} (Status code: {status})"
        ) from error
