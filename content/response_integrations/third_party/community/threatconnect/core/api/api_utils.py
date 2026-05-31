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

"""ThreatConnect V3 API utilities."""

from __future__ import annotations

import json
from typing import Any
from urllib.parse import urljoin

import requests

from ..constants import ENDPOINTS
from ..exceptions import InvalidRequestParametersError, ThreatConnectHTTPError

HTTP_422_UNPROCESSABLE_ENTITY = 422


def get_full_url(
    api_root: str,
    endpoint_id: str,
    endpoints: dict[str, str] | None = None,
    **kwargs: dict[str, Any],
) -> str:
    """Construct the full URL using a URL identifier and optional variables.

    Args:
        api_root (str): The root of the API endpoint.
        endpoint_id (str): The identifier for the specific URL.
        endpoints (dict[str, str], optional): endpoints dictionary object.
        kwargs (dict): Variables passed for string formatting.

    Returns:
        str: The full URL constructed from API root, endpoint identifier and variables.

    """
    endpoints = endpoints or ENDPOINTS
    return urljoin(api_root, endpoints[endpoint_id].format(**kwargs))


def validate_response(
    response: requests.Response,
    error_msg: str = "An error occurred",
) -> None:
    """Validate response.

    Args:
        response (requests.Response): Response to validate.
        error_msg (str): Default message to display on error.

    Raises:
        InvalidRequestParametersError: If the response status code is 422.
        ThreatConnectHTTPError: If there is any other error in the response.

    """
    try:
        if response.status_code == HTTP_422_UNPROCESSABLE_ENTITY:
            errors = response.json().get("query", {})
            err_msg = json.dumps(errors) if errors else "Unknown Error"
            raise InvalidRequestParametersError(err_msg)

        response.raise_for_status()

    except requests.HTTPError as error:
        content_str = error.response.content.decode("utf-8") if error.response.content else ""
        msg = f"{error_msg}: {error} {content_str}"
        raise ThreatConnectHTTPError(
            msg,
            status_code=error.response.status_code,
        ) from error
