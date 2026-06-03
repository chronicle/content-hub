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
    **kwargs: Any,
) -> str:
    """Construct the full URL using a URL identifier and optional variables.

    Args:
        api_root: The root of the API endpoint.
        endpoint_id: The identifier for the specific URL.
        endpoints: endpoints dictionary object.
        kwargs: Variables passed for string formatting.

    Returns:
        The full URL constructed from API root, endpoint identifier and variables.

    """
    endpoints = endpoints or ENDPOINTS
    return urljoin(api_root, endpoints[endpoint_id].format(**kwargs))


def validate_response(
    response: requests.Response,
    error_msg: str = "An error occurred",
) -> None:
    """Validate response.

    Args:
        response: Response to validate.
        error_msg: Default message to display on error.

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
        response = error.response
        content_str = (
            response.content.decode("utf-8")
            if response is not None and response.content
            else ""
        )
        status_code = response.status_code if response is not None else None
        msg = f"{error_msg}: {error} {content_str}"
        raise ThreatConnectHTTPError(
            msg,
            status_code=status_code,
        ) from error
