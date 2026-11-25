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

from bs4 import BeautifulSoup

from .constants import NOT_FOUND_STATUS, FORBIDDEN_STATUS, RATE_LIMIT_STATUS
from .exceptions import (
    InsufficientResourcePermissionError,
    ProjectNotFoundError,
    GoogleCloudPolicyIntelligenceError,
    MaximumRequestLimitError,
)


def validate_response(status_code: int, content: str | bytes) -> None:
    """Validate response

    Args:
        response_info: The response info from the request API
        content: The response content
    """

    if 200 <= status_code < 400:
        return

    try:
        content = json.loads(content)
    except json.decoder.JSONDecodeError:
        pass

    message = get_error_message_from_response(status_code, content)

    if status_code == FORBIDDEN_STATUS:
        raise InsufficientResourcePermissionError(f"{message}")

    if status_code == NOT_FOUND_STATUS:
        raise ProjectNotFoundError(f"{message}")

    if status_code == RATE_LIMIT_STATUS:
        raise MaximumRequestLimitError(f"{message}")

    raise GoogleCloudPolicyIntelligenceError(f"{message}")


def get_error_message_from_response(
    status_code: int, content: bytes | dict, error_msg: str = "An error occurred"
) -> str:
    """Gets the error message from the response content

    Args:
        status_code: Response status code
        content: Response content
        error_msg: Generic error message to be applied at the beginning of each
            error message
    Returns:
        An error message
    """

    if isinstance(content, dict):
        message = content.get("error", {}).get("message")
        error_text = message
    else:
        error_text = BeautifulSoup(content, "html.parser").p.text
    return f"{error_msg}: {error_text}\nResponse Status Code: {status_code}"
