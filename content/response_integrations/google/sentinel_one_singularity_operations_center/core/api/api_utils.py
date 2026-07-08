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
from typing import TYPE_CHECKING
from urllib.parse import urljoin

if TYPE_CHECKING:
    from collections.abc import Mapping

    import requests

from ..constants import ENDPOINTS
from ..exceptions import SentinelOneSingularityOperationsCenterError


def get_full_url(
    api_root: str,
    endpoint_id: str,
    endpoints: Mapping[str, str] | None = None,
    **kwargs: object,
) -> str:
    """Construct the full URL using a URL identifier and optional variables.

    Args:
        api_root (str): The root of the API endpoint
        endpoint_id (str): The identifier for the specific URL
        endpoints (dict[str, str]): endpoints dictionary object
        kwargs (dict): Variables passed for string formatting

    Returns:
        str: The full URL constructed from API root, endpoint identifier and variables

    """
    endpoints = endpoints or ENDPOINTS
    # Strip trailing slash from api_root and leading slash from endpoint if needed
    base = api_root if api_root.endswith("/") else f"{api_root}/"
    endpoint = endpoints[endpoint_id]
    endpoint = endpoint.removeprefix("/")
    return urljoin(base, endpoint.format(**kwargs))


def validate_response(
    response: requests.Response,
    error_msg: str = "An error occurred",
) -> None:
    """Validate response.

    Args:
        response (requests.Response): Response to validate
        error_msg (str): Default message to display on error

    Raises:
        SentinelOneSingularityOperationsCenterError: If there is any error in the response

    """
    try:
        response.raise_for_status()
    except Exception as error:
        msg = f"{error_msg}: {error}"
        raise SentinelOneSingularityOperationsCenterError(msg) from error

    try:
        response_json = response.json()
    except ValueError as error:
        msg = f"{error_msg}: Response is not valid JSON."
        raise SentinelOneSingularityOperationsCenterError(msg) from error

    if isinstance(response_json, dict) and "errors" in response_json:
        errors = response_json["errors"]
        err_msg = json.dumps(errors) if errors else "GraphQL Error"
        msg_0 = f"{error_msg}: {err_msg}"
        raise SentinelOneSingularityOperationsCenterError(msg_0)
