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

import urllib.parse
import requests

from ..core.SysdigSecureConstants import ENDPOINTS
from ..core.SysdigSecureExceptions import SysdigSecureHTTPException


def get_full_url(
    api_root: str,
    endpoint_id: str,
    endpoints: dict[str, str] = None,
    **kwargs
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
    return urllib.parse.urljoin(api_root, endpoints[endpoint_id].format(**kwargs))


def validate_response(
    response: requests.Response,
    error_msg: str = "An error occurred",
) -> None:
    """Validate response

    Args:
        response (requests.Response): Response to validate
        error_msg (str): Default message to display on error

    Raises:
        SysdigSecureHTTPException: If there is any error in the response
    """
    try:
        response.raise_for_status()

    except requests.HTTPError as error:
        raise SysdigSecureHTTPException(
            f"{error_msg}: {error} {error.response.content}",
            status_code=error.response.status_code
        ) from error
