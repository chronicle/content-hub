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

from TIPCommon.transformation import convert_list_to_comma_string
from nmap.core import constants
from nmap.core import exceptions


def validate_ip_address(ips: list[str]) -> None:
    """Validates whether an IP address is valid.

    Args:
        ip(str): The IP address to validate.

    Raises:
        NmapValidationError: If the IP addresses is invalid.
    """
    if not ips:
        return

    invalid_ips = []
    for ip in ips:
        try:
            ipaddress.ip_address(ip.strip())
        except ValueError:
            invalid_ips.append(ip)

    if invalid_ips:
        raise exceptions.NmapValidationError(
            f"The following IP addresses are invalid: "
            f"{convert_list_to_comma_string(invalid_ips)}. "
            "Please provide valid IP addresses."
        )


def validate_nmap_root_required_options(options_string: str) -> None:
    """Validate if the provided Nmap options require root privileges.

    Args:
        options_string(str): The Nmap options string to validate for root privileges.

    Raises:
        NmapValidationError: If the Nmap options require root privileges.
    """
    options: list[str] = options_string.split()
    root_required_options: list[str] = []
    for opt in options:
        if opt in constants.NMAP_ROOT_REQUIRED_OPTIONS:
            root_required_options.append(opt)

    if root_required_options:
        raise exceptions.NmapValidationError(
            "The following options "
            f"'{convert_list_to_comma_string(root_required_options)}' "
            "requires root privileges and are not permitted for this scan."
        )
