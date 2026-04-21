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

from TIPCommon.types import SingleJson
from . import exceptions
from . import constants


def validate_response(
    response: SingleJson,
    error_msg: str | None = "An error occurred",
) -> None:
    """Validate Google Forms response

    Args:
        response(json/html): Response from Google Forms api
        error_msg(str): Error message to display.
    """
    try:
        if response.status_code == constants.API_BAD_REQUEST_STATUS_CODE:
            raise exceptions.GoogleFormsValidationException(
                f"{error_msg}: {response.json().get('error', {}).get('message')}"
            )
        response.raise_for_status()

    except requests.HTTPError as error:
        try:
            response.json()

        except json.JSONDecodeError as err:
            error_message = f"{error_msg}: {error.response.content}"
            raise exceptions.GoogleFormsManagerError(error_message) from err

        raise exceptions.GoogleFormsManagerError(
            f"{error_msg}: {response.json().get('error', {}).get('message')}"
        ) from error


def get_full_url(
    api_root: str,
    url_id: str,
    connector_api: bool = False,
    **kwargs,
) -> str:
    """Gets the full URL based on the provided URL ID.

    Args:
        url_id: The key of the URL in the ENDPOINTS or CONNECTOR_ENDPOINTS
        dictionary.
        connector_api:  A boolean indicating whether to use the connector API root
        or the main API root.
        **kwargs: Keyword arguments for string formatting.

    Returns:
        str: The full URL.
    """
    endpoints = constants.CONNECTOR_ENDPOINTS if connector_api else constants.ENDPOINTS
    return urljoin(api_root, endpoints[url_id].format(**kwargs))
