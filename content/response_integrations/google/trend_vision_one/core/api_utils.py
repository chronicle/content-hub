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

from typing import Any

import requests

from .TrendVisionOneExceptions import TrendVisionOneException


def validate_response(response, error_msg="An error occurred"):
    """
    Validate response
    Args:
        response (requests.Response): The response to validate
        error_msg (str): Default message to display on error

    Raises:
        TrendVisionOneException: If the response status is not successful.
    """
    try:
        response.raise_for_status()

    except requests.HTTPError as error:
        try:
            error_content: dict[str, Any] = response.json()
            error_message: str = error_content["error"]["message"]
            raise TrendVisionOneException(error_message) from error

        except (ValueError, KeyError):
            pass

        raise TrendVisionOneException(
            f"{error_msg}: {error} {error.response.content}"
        ) from error
