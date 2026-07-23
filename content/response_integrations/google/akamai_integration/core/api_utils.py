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

from urllib.parse import urljoin
import requests

from ..core.constants import ENDPOINTS, FAILED_TO_TAKE_REQUEST_DOWN_ERR
from ..core.exceptions import AkamaiManagerError, AuthenticationError, RequestTakeDownError


def get_full_url(api_root: str, url_id: str, **kwargs) -> str:
    return urljoin(api_root, ENDPOINTS[url_id].format(**kwargs))


def validate_response(
    response: requests.Response,
    error_msg: str = "An error occurred",
) -> None:
    """Validate response

    Args:
        response (requests.Response): The response to validate
        error_msg (str): Default message to display on error.
            Defaults to 'An error occurred'.

    """
    try:
        response.raise_for_status()

    except requests.exceptions.HTTPError as http_error:
        try:
            error_details = response.json()

        except requests.exceptions.JSONDecodeError as e:
            raise AkamaiManagerError("Invalid request.") from e

        if error_details.get("detail", ""):
            raise AuthenticationError(error_details["detail"]) from http_error

        if FAILED_TO_TAKE_REQUEST_DOWN_ERR in error_details.get("error", "").lower():
            raise RequestTakeDownError(error_details.get("error")) from http_error

        raise AkamaiManagerError(
            f"{error_msg}: {http_error} {response.content}",
        ) from http_error
