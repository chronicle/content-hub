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
import re

import requests

STORED_IDS_LIMIT = 3000
TIMEOUT_THRESHOLD = 0.9


def validate_response(response, error_msg="An error occurred"):
    """
    Validate response
    :param response: {requests.Response} The response to validate
    :param error_msg: {str} Default message to display on error
    """
    try:
        response.raise_for_status()

    except requests.HTTPError as error:
        raise Exception(f"{error_msg}: {error} {error.response.content}")

    return True


def mask_string(string):
    """
    Mask given string
    :param string: {str} The string to mask
    :return: {str} The masked string
    """
    string = re.sub("\d", "0", string)
    string = re.sub("[a-zA-Z]", "X", string)
    return string


def get_milliseconds_from_minutes(minutes):
    """
    Get milliseconds from minutes
    :param minutes: {int} The minutes
    :return: {int} The milliseconds
    """
    return minutes * 60 * 1000
