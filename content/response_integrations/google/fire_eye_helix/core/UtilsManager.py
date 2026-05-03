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
import datetime
from ipaddress import ip_address, IPv4Address

import requests
from dateutil import parser
from dateutil.tz import tzoffset

from .FireEyeHelixConstants import ITEM_TYPES
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyUtils import get_email_address, get_domain_from_entity

UNIX_FORMAT = 1
DATETIME_FORMAT = 2


def naive_time_converted_to_aware(time_param, timezone_offset):
    """
    Converts naive time to aware time
    :param timezone_offset: UTC timezone offset
    :param time_param: Naive time to convert
    :return: {datetime}
    """
    parsed_date = parser.parse(time_param)
    return datetime.datetime(
        parsed_date.year,
        parsed_date.month,
        parsed_date.day,
        parsed_date.hour,
        parsed_date.minute,
        parsed_date.second,
        tzinfo=get_server_tzoffset(timezone_offset),
    )


def get_server_tzoffset(server_timezone):
    """
    get server timezone offset from utc
    :param server_timezone {str} UTC timezone offset
    :return: {tzoffset}
    """
    return tzoffset(None, float(server_timezone) * 60 * 60)


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


def get_item_type_and_value(entity):
    """
    Get item type and value from entity
    :param entity: {str} The Siemplify entity
    :return: {tuple} Item type and item value
    """
    item_type = ITEM_TYPES.get("misc")
    item_value = entity.identifier

    if entity.entity_type == EntityTypes.FILEHASH and len(entity.identifier) == 40:
        item_type = ITEM_TYPES.get("sha1")
    elif entity.entity_type == EntityTypes.FILEHASH and len(entity.identifier) == 32:
        item_type = ITEM_TYPES.get("md5")
    elif entity.entity_type == EntityTypes.URL:
        item_type = ITEM_TYPES.get("fqdn")
        item_value = get_domain_from_entity(entity)
    elif entity.entity_type == EntityTypes.USER and get_email_address(entity):
        item_type = ITEM_TYPES.get("email")
    elif entity.entity_type == EntityTypes.ADDRESS:
        try:
            ipv4 = ITEM_TYPES.get("ipv4")
            ipv6 = ITEM_TYPES.get("ipv6")
            item_type = (
                ipv4 if type(ip_address(entity.identifier)) is IPv4Address else ipv6
            )
        except ValueError:
            pass

    return item_type, item_value
