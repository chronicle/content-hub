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
import hashlib
import json
from typing import TYPE_CHECKING

from soar_sdk.SiemplifyConnectors import SiemplifyConnectorExecution
from TIPCommon.consts import NUM_OF_MILLI_IN_SEC, NUM_OF_MIN_IN_HOUR, NUM_OF_SEC_IN_MIN
from TIPCommon.data_models import AlertCard
from TIPCommon.smp_io import read_content, write_content

from .constants import (
    CONTEXT_VALUE_CHUNK_LIMIT,
    CONTEXT_VALUE_CHUNK_SIZE,
    CONTEXT_VALUE_CHUNK_SIZE_REDUCTION,
    ENTITY_TYPE,
    INCIDENT_ID_CONTEXT_PROPERTY,
    SPECIAL_CHARACTERS_MAPPING,
    PLACEHOLDER_START,
    PLACEHOLDER_END,
    CHARACTERS_LIMIT,
    GLOBAL_TIMEOUT_THRESHOLD_IN_MIN,
)

if TYPE_CHECKING:
    from typing import Any, TypeAlias

    from TIPCommon.types import ChronicleSOAR, SingleJson

    IncidentCache: TypeAlias = dict[str, SingleJson]


class LOGGER:
    def __init__(self, logger):
        self.logger = logger

    def info(self, msg):
        if self.logger:
            self.logger.info(msg)

    def error(self, msg):
        if self.logger:
            self.logger.error(msg)

    def exception(self, msg):
        if self.logger:
            self.logger.exception(msg)


def string_to_multi_value(string_value, delimiter=",", only_unique=False):
    # type: (str, str, bool) -> list
    """
    String to multi value.
    @param string_value: {str} String value to convert multi value.
    @param delimiter: {str} Delimiter to extract multi values from single value string.
    @param only_unique: {bool} include only uniq values
    """
    if not string_value:
        return []
    values = [
        single_value.strip()
        for single_value in string_value.split(delimiter)
        if single_value.strip()
    ]
    if only_unique:
        seen = set()
        return [value for value in values if not (value in seen or seen.add(value))]
    return values


def convert_list_to_comma_separated_string(iterable):
    # type: (list or set) -> str
    """
    Convert list to comma separated string
    @param iterable: List or Set to covert
    """
    return ", ".join(iterable)


def convert_list_to_comma_string(value_list, delimiter=", "):
    if not value_list:
        return ""

    return delimiter.join(value_list) if isinstance(value_list, list) else value_list


def handle_special_characters(string):
    """
    Replace special characters in string
    :param string: {str} string to transform
    :return {str} transformed string
    """
    for key, value in SPECIAL_CHARACTERS_MAPPING.items():
        string.replace(key, value)

    return string


def transform_template_string(template, data):
    """
    Transform string containing template using provided data
    :param template: {str} string containing template
    :param data: {dict} data to use for transformation
    :return: {str} transformed string
    """
    index = 0

    while PLACEHOLDER_START in template[index:] and PLACEHOLDER_END in template[index:]:
        partial_template = template[index:]
        start, end = (
            partial_template.find(PLACEHOLDER_START) + len(PLACEHOLDER_START),
            partial_template.find(PLACEHOLDER_END),
        )
        substring = partial_template[start:end]
        value = data.get(substring) if data.get(substring) else ""
        if type(value) in [str, int, float]:
            value = str(value)
        template = template.replace(
            f"{PLACEHOLDER_START}{substring}{PLACEHOLDER_END}", value, 1
        )
        index = index + start + len(value)

    return template


def get_value_from_template(template, data, default_value, char_limit=CHARACTERS_LIMIT):
    """
    This method gets a value from a template and data
    :param template: {str} The template to get the value from
    :param data: {dict} The data to get the value from
    :param default_value: {str} The default value to return if the value is not found
    :param char_limit: {int} The maximum length of the value
    :return: {str} The value
    """
    value = transform_template_string(template, data) if template else default_value
    return value[:char_limit]


def find_fallback_value(source_dicts, fallbacks_list):
    """
    This method is used to get fallback value from list of dicts
    :param source_dicts: List[Dict] List of dicts sorted by priority to extract fallback data from
    :param fallbacks_list: List[str] List of field sorted by priority with keys for extraction
    """
    for item in fallbacks_list:
        for source_dict in source_dicts:
            if item in source_dict:
                return source_dict[item], item
    return None, None


def is_async_action_global_timeout_approaching(siemplify, start_time):
    return (
        siemplify.execution_deadline_unix_time_ms - start_time
        < GLOBAL_TIMEOUT_THRESHOLD_IN_MIN * 60
    )


def dict_to_md5_hash(dictionary: dict) -> str:
    """Convert a dictionary to an MD5 hash string

    Args:
        dictionary (dict): dictionary to convert to an MD5 hash

    Returns:
        str: converted MD5 hash string
    """
    return hashlib.md5(
        json.dumps(order_dict_values(dictionary), sort_keys=True).encode()
    ).hexdigest()


def convert_hours_to_milliseconds(hours: int) -> int:
    """
    Convert hours to milliseconds
    Args:
        hours (int): hours to convert

    Returns:
        int: converted milliseconds
    """
    return hours * NUM_OF_MIN_IN_HOUR * NUM_OF_SEC_IN_MIN * NUM_OF_MILLI_IN_SEC


def get_chunks_as_context_property(
    connector_scope: SiemplifyConnectorExecution, key: str
) -> dict:
    """
    Get context properties chunks per key prefix and unique counter

    Args:
        connector_scope (SiemplifyConnectorExecution): connector scope
        key (str): context property key prefix

    Returns:
        dict: dict of all chunks
    """
    counter = 0
    chunks = {}

    while True:
        chunk = read_content(
            connector_scope,
            file_name=f"{key}_{counter}.json",
            db_key=f"{key}_{counter}",
            default_value_to_return={},
        )

        if not chunk:
            break

        chunks.update(chunk)
        counter += 1

    return chunks


def set_chunks_as_context_property(
    connector_scope: SiemplifyConnectorExecution, key: str, chunks: list[dict]
):
    """
    Set context properties per each chunk with key prefix and unique counter

    Args:
        connector_scope (SiemplifyConnectorExecution): connector scope
        key (str): key prefix
        chunks ([dict]): list of chunks to set
    """
    counter = 0

    for chunk in chunks:
        write_content(
            connector_scope,
            content_to_write=chunk,
            file_name=f"{key}_{counter}.json",
            db_key=f"{key}_{counter}",
            default_value_to_set={},
        )

        counter += 1


def split_dict_into_chunks(
    original_dict: IncidentCache,
    chunk_size: int = CONTEXT_VALUE_CHUNK_SIZE,
    chunk_limit: int = CONTEXT_VALUE_CHUNK_LIMIT,
) -> list[IncidentCache]:
    """Split a dictionary into chunks whose JSON-serialized size remains under
    chunk_limit.

    Args:
        original_dict (IncidentCache): The original dictionary to partition.
        chunk_size (int): Custom item count limit per chunk
        (kept for backward compatibility).
        chunk_limit (int): Maximum JSON-serialized character length per chunk.

    Returns:
        list[IncidentCache]: List of successfully partitioned sub-dictionaries.
    """
    if not original_dict:
        return []

    sizes = {
        key: len(json.dumps({key: val}))
        for key, val in original_dict.items()
    }

    for key, size in sizes.items():
        if size > chunk_limit:
            raise ValueError(
                f"A single item in dictionary exceeds the chunk limit and cannot be split: "
                f"'{key}' ({size} > {chunk_limit})"
            )

    chunks = []
    current_chunk = {}
    current_size = 0

    for key, val in original_dict.items():
        item_size = sizes[key]

        if current_chunk and (current_size + item_size > chunk_limit):
            chunks.append(current_chunk)
            current_chunk = {key: val}
            current_size = item_size
        else:
            current_chunk[key] = val
            current_size += item_size

    if current_chunk:
        chunks.append(current_chunk)

    return chunks


def order_dict_values(dictionary: dict[str, Any]) -> dict[str, Any]:
    """
    Order dictionary values

    Args:
        dictionary (dict[str, Any]): dictionary to order values
    Returns:
        dict[str, Any]: dictionary with ordered values
    """
    ordered_dict = {}

    def _order_value(value):
        if isinstance(value, dict):
            return {
                nested_key: _order_value(nested_value)
                for nested_key, nested_value in value.items()
            }
        if isinstance(value, list):
            return order_list([_order_value(item) for item in value])

        try:
            return _order_value(json.loads(value))
        except (json.decoder.JSONDecodeError, TypeError):
            return value

    for dict_key, dict_value in dictionary.items():
        ordered_dict[dict_key] = _order_value(dict_value)

    return ordered_dict


def order_list(lst: list[Any]) -> list[Any]:
    """
    Order list of items containing mixed data types

    Args:
        lst (list[Any]): list to order

    Returns:
        list[Any]: ordered list
    """
    return sorted(lst, key=lambda x: (isinstance(x, bool), isinstance(x, str), str(x)))


def get_incident_id_from_alert(
    chronicle_soar: ChronicleSOAR,
    alert: AlertCard,
) -> str | None:
    """
    Extracts a Sentinel incident ID from a single Google SecOps alert.

    Args:
        chronicle_soar (ChronicleSOAR) : The Chronicle SOAR object used to
            interact with the platform.
        alert (SingleJson): A dictionary representing the Google SecOps alert.

    Returns:
        str | None: The Sentinel incident ID if found, otherwise None.
    """
    if hasattr(alert, "additional_properties") and isinstance(
        alert.additional_properties, str
    ):
        try:
            json_object = json.loads(alert.additional_properties)
            ticket_id = json_object.get("graph_incident_id")
            if ticket_id:
                return ticket_id
        except (json.JSONDecodeError, KeyError) as e:
            print(f"Error parsing additionalProperties: {e}")

    if hasattr(alert, "alert_group_identifier") and alert.alert_group_identifier:
        return chronicle_soar.get_context_property(
            ENTITY_TYPE, alert.alert_group_identifier, INCIDENT_ID_CONTEXT_PROPERTY
        )

    return None


def strip_html_tags(text: str) -> str:
    """Removes HTML tags from a string."""
    clean = re.compile("<.*?>")
    return re.sub(clean, "", text)
