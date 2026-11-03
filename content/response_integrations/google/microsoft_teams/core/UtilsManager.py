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

import itertools
from typing import Any
from bs4 import BeautifulSoup

from soar_sdk.SiemplifyUtils import unix_now
from .datamodels import Message
from .MicrosoftConstants import DEFAULT_CONTENT_TYPE

GLOBAL_TIMEOUT_THRESHOLD_IN_MIN = 1
TIMEOUT_THRESHOLD = 0.9


def is_approaching_timeout(
    python_process_timeout, connector_starting_time, timeout_threshold=TIMEOUT_THRESHOLD
):
    """
    Check if a timeout is approaching.
    :param python_process_timeout: {int} The python process timeout
    :param connector_starting_time: {int} The connector start unix time
    :param timeout_threshold: {int} Determines which part of the execution time is available for execution
    :return: {bool} True if timeout is close, False otherwise
    """
    processing_time_ms = unix_now() - connector_starting_time
    return processing_time_ms > python_process_timeout * 1000 * timeout_threshold


def is_async_action_global_timeout_approaching(siemplify, start_time):
    return (
        siemplify.execution_deadline_unix_time_ms - start_time
        < GLOBAL_TIMEOUT_THRESHOLD_IN_MIN * 60
    )


def string_to_multi_value(string_value, delimiter=",", only_unique=False):
    """
    String to multi value.
    :param string_value: {str} String value to convert multi value.
    :param delimiter: {str} Delimiter to extract multi values from single value string.
    :param only_unique: {bool} include only unique values
    :return: {dict} fixed dictionary.
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


def get_content_values(reply_data: dict[str, Any]) -> tuple[str, str]:
    """Get raw content value and parsed content value for contentType 'html' from reply
        JSON.

    Args:
        reply_data (dict): reply data from the API response.

    Returns:
        tuple[str, str]: tuple of content value as text and parsed content value if
            contentType is 'html' from reply.
    """
    body = reply_data.get("body", {})
    content_type = body.get("contentType", "")
    content = body.get("content", "")
    parsed_content = (
        content
        if content_type == DEFAULT_CONTENT_TYPE
        else BeautifulSoup(content, "html.parser").text.strip()
    )

    return content, parsed_content


def get_first_msg_after_a_msg_id_with_different_sender_id(
    message_id: str, sender_id: str, messages: list[Message]
) -> Message | None:
    """
    Retrieves the first message after a specified message ID from a list of messages.

    Args:
        message_id (str): The ID of the message to find the message after.
        sender_id (str): The ID of the sender of message.
        messages (list[Message]): The list of Message objects.

    Returns:
        Message: The first message after the specified message ID, or None if not found.
    """
    start_index = next(
        (i for i, m in enumerate(messages) if m.message_id == message_id), len(messages)
    )
    for message in itertools.islice(messages, start_index, None):
        if message.sender != sender_id:
            return message

    return None
