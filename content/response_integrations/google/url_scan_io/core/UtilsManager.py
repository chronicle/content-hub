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

from typing import Any, Callable
import base64
import tldextract
from datetime import datetime, timezone


def get_entity_original_identifier(entity):
    """
    Helper function for getting entity original identifier
    :param entity: entity from which function will get original identifier
    :return: {str} original identifier
    """
    return entity.additional_properties.get("OriginalIdentifier", entity.identifier)


def get_screenshot_content_base64(content):
    """
    Get image base64 encoded by image content
    :param content: {str} Image src
    :return: {bytes} base64 string
    """
    return base64.b64encode(content)


def get_domain_from_entity(identifier):
    """
    Extract domain from entity identifier
    :param identifier: {str} the identifier of the entity
    :return: {str} domain part from entity identifier
    """
    if "@" in identifier:
        return identifier.split("@", 1)[-1]
    try:
        result = tldextract.extract(identifier)
        if result.suffix:
            return ".".join([result.domain, result.suffix])
        return result.domain
    except ImportError:
        raise ImportError("tldextract is not installed. Use pip and install it.")


def timestamp_to_iso(timestamp):
    """
    Function that changes the timestamp to a human-readable format
    :param timestamp: {int} Unix Timestamp
    :return: {str} Timestamp in human readable form
    """
    return datetime.fromtimestamp(timestamp, tz=timezone.utc).isoformat(" ", "seconds")


def format_dict_keys(
    input_data: dict[str, Any],
    key_formatter: Callable[[str], str] = lambda key: key.strip(),
) -> dict[str, Any]:
    """
    Recursively formats keys in a dictionary by stripping leading and trailing spaces.

    Args:
        input_dict (dict[str, Any]): Input data to strip key's for it.
        key_formatter (Callable[[str], str]): Custom key formatter function.

    Returns:
        dict[str, Any]: Formatted dictionary with keys stripped of leading and
        trailing spaces.
    """
    if isinstance(input_data, dict):
        output_data = {}
        for key, value in input_data.items():
            output_data[key_formatter(key)] = format_dict_keys(value, key_formatter)

        return output_data

    if isinstance(input_data, list):
        return [format_dict_keys(item, key_formatter) for item in input_data]

    return input_data
