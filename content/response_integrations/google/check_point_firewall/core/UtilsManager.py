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
import os
from .constants import NOT_FOUND_CODE, INVALID_PARAMETERS_CODE
from .exceptions import (
    CheckpointManagerError,
    CheckpointManagerBadRequestException,
    CheckpointManagerNotFoundException,
)


def validate_response(response):
    """
    Validate response
    :param response: {requests.Response} The response to validate
    """
    try:
        response.raise_for_status()
    except requests.HTTPError as error:
        if response.status_code == NOT_FOUND_CODE:
            raise CheckpointManagerNotFoundException(error)
        if response.status_code == INVALID_PARAMETERS_CODE:
            raise CheckpointManagerBadRequestException(error)
        raise CheckpointManagerError(error)


def save_attachment(path, name, content):
    """
    Save attachment to local path
    :param path: {str} Path of the folder, where files should be saved
    :param name: {str} File name to be saved
    :param content: {str} File content
    :return: {str} Path to the downloaded files
    """
    # Create path if not exists
    if not os.path.exists(path):
        os.makedirs(path)
    # File local path
    local_path = os.path.join(path, name)
    with open(local_path, "wb") as file:
        file.write(content)
        file.close()

    return local_path
