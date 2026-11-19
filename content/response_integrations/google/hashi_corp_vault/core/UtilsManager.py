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
from .HashiCorpVaultExceptions import HashiCorpVaultException, NotFoundException


def validate_response(response, error_msg="An error occurred"):
    """
    Validate response
    Args:
        response (requests.Response): The response to validate
        error_msg (str): Default message to display on error

    Returns:
        True, if successful, HashiCorpVaultException otherwise
    """
    try:
        response.raise_for_status()

    except requests.HTTPError as error:
        try:
            error_messages = response.json().get("errors", [])
            error_string = (
                "\n".join(error_messages) if error_messages else response.status_code
            )

            if "not found" in error_string.casefold():
                raise NotFoundException(error_string)
            raise HashiCorpVaultException(error_string)

        except (ValueError, KeyError):
            pass

        raise HashiCorpVaultException(f"{error_msg}: {error} {error.response.content}")
