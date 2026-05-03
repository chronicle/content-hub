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
import requests
from .StellarCyberStarlightExceptions import StellarCyberInvalidApiKeyError

from .StellarCyberStarlightConstants import (
    UNAUTHORIZED_STATUS_CODE,
    UNAUTHORISED_ERROR_MESSAGE,
    ACCESS_TOKEN_CHECK,
)


def validate_response(response, error_msg="An error occurred"):
    """
    Validate response
    :param response: {requests.Response} The response to validate
    :param error_msg: {str} Default message to display on error
    """
    try:
        response.raise_for_status()

    except requests.HTTPError as error:
        try:
            error_message = error.args[0]
        except Exception:
            error_message = ""
        if response.status_code == UNAUTHORIZED_STATUS_CODE:
            if ACCESS_TOKEN_CHECK in error_message:
                raise StellarCyberInvalidApiKeyError(
                    UNAUTHORISED_ERROR_MESSAGE.format(value="API Token")
                )
            else:
                raise StellarCyberInvalidApiKeyError(
                    UNAUTHORISED_ERROR_MESSAGE.format(value="API Key")
                )
        raise Exception(f"{error_msg}: {error} {error.response.content}")

    return True


def find_fallback_value(source_dicts, fallbacks_list, default_value=None):
    """
    This method is used to get fallback value from list of dicts
    :param source_dicts: {list} List of dicts to extract fallback data from
    :param fallbacks_list: {list} List of fallback fields sorted by priority
    :param default_value: {str} default value to use if no fallback is found
    """
    for key in fallbacks_list:
        for source_dict in source_dicts:
            if key in source_dict:
                return source_dict[key]

    return default_value
