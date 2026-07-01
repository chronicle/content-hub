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

from ..core.constants import ENDPOINTS, INVALID_CREDS
from ..core.ExtrahopExceptions import (
    ExtrahopException,
    InvalidCredentialsError,
    InvalidDetectionIDError,
)


def get_full_url(api_root: str, url_id: str, **kwargs) -> str:
    return urljoin(api_root, ENDPOINTS[url_id].format(**kwargs))


def validate_response(
    response: requests.Response,
    error_msg: str = "An error occurred",
) -> None:
    """Validate response.

    Args:
        response(requests.Response): The response to validate.
        error_msg(str): Default message to display on error
    """
    try:
        response.raise_for_status()
    except requests.exceptions.HTTPError as error:
        try:
            error_details = response.json()
        except Exception as e:
            raise ExtrahopException(
                f"{error_msg}: {error} {error.response.content}"
            ) from e
        if INVALID_CREDS in error_details.get("error", "").lower():
            raise InvalidCredentialsError(
                "Please check the credentials. Either "
                'invalid "Client ID or Client Secret."'
            ) from error
        if response.status_code == 404:
            raise InvalidDetectionIDError("Detection not found.") from error

        raise ExtrahopException(
            f"{error_msg}: {error} {response.json().get('message') or response.content}"
        ) from error
