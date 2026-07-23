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

import ipaddress
from typing import TYPE_CHECKING

import requests

from ..core.constants import (
    GENERIC_AUTH_FAILED_ERROR,
    UNAUTHORIZED_STATUS_CODE,
    BAD_REQUEST_STATUS_CODE,
    EXCEEDED_RATE_LIMIT_STATUS_CODE,
)
from ..core.exceptions import ZscalerManagerError

if TYPE_CHECKING:
    from TIPCommon.base.interfaces.logger import ScriptLogger
    from TIPCommon.types import SingleJson


def is_valid_ip(address: str) -> bool:
    """Check if address is a valid IP."""
    try:
        ipaddress.ip_address(address)
        return True
    except ValueError:
        return False


class Logger:
    def __init__(self, logger: ScriptLogger | None) -> None:
        self.logger: ScriptLogger | None = logger

    def info(self, msg: str) -> None:
        if self.logger:
            self.logger.info(msg)


def validate_response(
    response: requests.Response,
    error_msg: str = GENERIC_AUTH_FAILED_ERROR,
) -> None:
    """Validate response.

    Args:
        response: The HTTP response from requests.
        error_msg: Default message to display on 401 error.

    Raises:
        ZscalerManagerError: If response indicates a failure.
    """

    try:
        if response.status_code in (
            UNAUTHORIZED_STATUS_CODE,
            BAD_REQUEST_STATUS_CODE,
        ):
            try:
                error_json: SingleJson = response.json()
                err_val: str | None = error_json.get("message") or error_json.get(
                    "error"
                )
                api_message: str = f" API Error: {err_val}" if err_val else ""
            except ValueError:
                api_message: str = " API Error: Invalid response format from server."

            if response.status_code == UNAUTHORIZED_STATUS_CODE:
                raise ZscalerManagerError(f"{error_msg}{api_message}")
            raise ZscalerManagerError(f"Bad Request.{api_message}")

        if response.status_code == EXCEEDED_RATE_LIMIT_STATUS_CODE:
            raise ZscalerManagerError("Error: you exceed the API request rate limit")

        response.raise_for_status()

    except requests.HTTPError as error:
        raise ZscalerManagerError(
            f"Error: {error}. Status code: {response.status_code}. "
            f"{error.response.content}"
        ) from error
