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

from ipaddress import IPv4Address, ip_address

import requests
from soar_sdk.SiemplifyUtils import unix_now

from .constants import ASYNC_ACTION_TIMEOUT_THRESHOLD_MS, IPV4_TYPE, IPV6_TYPE
from .exceptions import BadRequestException, CiscoOrbitalException


def validate_response(response, error_msg="An error occurred"):
    """Validate response
    :param response: {requests.Response} The response to validate
    :param error_msg: {str} Default message to display on error
    """
    try:
        response.raise_for_status()

    except requests.HTTPError as error:
        if response.status_code == 400:
            msg = f"{error_msg}: {error} {error.response.content}"
            raise BadRequestException(
                msg
            ) from error

        msg = f"{error_msg}: {error} {error.response.content}"
        raise CiscoOrbitalException(
            msg
        ) from error

    return True


def get_dict_from_string(string):
    """Convert key:value string to dictionary
    :param string: {str} The string to convert
    :return: {dict} The converted dictionary
    """
    res = [map(str.strip, sub.split(":", 1)) for sub in string.split(",") if ":" in sub]

    return dict(res)


def get_ip_type(ip):
    """Check if ip is IPv4 or IPv6 or Invalid
    :param ip: {str} The given ip to check
    :return: {str} The type of ip
    """
    try:
        return IPV4_TYPE if type(ip_address(ip)) is IPv4Address else IPV6_TYPE
    except ValueError:
        pass


def is_action_approaching_timeout(python_process_timeout):
    """Check if a action script timeout is approaching.
    :param python_process_timeout: {int} The python process timeout
    :return: {bool} True if timeout is approaching, otherwise False
    """
    return unix_now() >= python_process_timeout - ASYNC_ACTION_TIMEOUT_THRESHOLD_MS


def hours_to_milliseconds(hours):
    """Convert hours to milliseconds
    :param hours: {int} Value in hours
    :return: {int} Converted value to milliseconds
    """
    return hours * 60 * 60 * 1000
