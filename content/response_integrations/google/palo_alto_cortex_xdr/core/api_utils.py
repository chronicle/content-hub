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
from ..core.constants import ALREADY_EXISTS_ERR_CODE, ALREADY_EXISTS_ERR_MSG
from ..core.exceptions import XDRException, XDRAlreadyExistsException, XDRPermissionException


def validate_response(
    response: requests.Response,
    error_msg: str = "An error occurred",
) -> None:
    """Validate the response from the API call.
    Args:
        response (requests.Response): The response object from the API call.
        error_msg (str): The error message to raise if the response is not valid.
    Raises:
        XDRException: If the response contains an error.
        XDRAlreadyExistsException: If the response indicates that the resource already
        exists.
        XDRPermissionException: If the response indicates 403 Forbidden.
    """
    try:
        response.raise_for_status()

    except requests.HTTPError as error:
        if response.status_code == 403:
            try:
                resp_json = response.json()
                details = f"{resp_json.get('reply', {}).get('err_msg')}-{resp_json.get('reply', {}).get('err_extra', response.content)}"
            except ValueError:
                details = response.content.decode('utf-8') if response.content else str(error)
            raise XDRPermissionException(f'{error_msg}:{details}') from error
            
        try:
            response.json()
        except ValueError as e:
            raise XDRException(f"{error_msg}: {error} - {response.content}") from e

        if (
            response.json().get("reply", {}).get("err_code") == ALREADY_EXISTS_ERR_CODE
            and response.json().get("reply", {}).get("err_extra")
            == ALREADY_EXISTS_ERR_MSG
        ):
            raise XDRAlreadyExistsException(
                f'{response.json().get("reply", {}).get("err_msg")} - '
                f'{response.json().get("reply", {}).get("err_extra", response.content)}'
            ) from error

        raise XDRException(
            f'{error_msg}: {response.json().get("reply", {}).get("err_msg")} - '
            f'{response.json().get("reply", {}).get("err_extra", response.content)}'
        ) from error
