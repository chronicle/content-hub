# Copyright 2025 Google LLC
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

from typing import TYPE_CHECKING

from urllib.parse import urljoin
import requests

from .constants import ENDPOINTS, ISSUE_NOT_FOUND_ERRORS, UNAUTHORIZED_STATUS_CODE
from .exceptions import InvalidCredsError, IssueNotFoundError, WizManagerError

if TYPE_CHECKING:
    from collections.abc import Sequence

    from TIPcommon.types import SingleJson


def get_full_url(api_root: str, url_id: str, **kwargs) -> str:
    return urljoin(api_root, ENDPOINTS[url_id].format(**kwargs))


def validate_response(
    response: requests.Response,
    error_msg: str = "An error occurred",
) -> None:
    """
    Validate a GraphQL HTTP response.

    Raises:
        requests.HTTPError: For non-200 HTTP responses.
        WizManagerError: For unexpected response formats or GraphQL errors.
    """
    try:
        response.raise_for_status()

    except requests.exceptions.HTTPError as http_error:
        if response.status_code == UNAUTHORIZED_STATUS_CODE:
            raise InvalidCredsError(
                "Invalid credentials provided. Please check the integration configuration."
            ) from http_error

        raise requests.HTTPError(f"{error_msg}: {http_error}") from http_error

    try:
        response_json = response.json()

    except ValueError as json_error:
        raise WizManagerError(f"{error_msg}: Response is not valid JSON.") from json_error

    if "errors" in response_json:
        graphql_errors: Sequence[SingleJson] = response_json["errors"]
        error_detail: str = graphql_errors[0].get("message", "Unknown error")
        if error_detail.lower() in ISSUE_NOT_FOUND_ERRORS:
            raise IssueNotFoundError(error_detail)

        raise WizManagerError(f"{error_msg}: {error_detail}")
