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

from functools import partial
import json
from typing import Callable

from TIPCommon.types import SingleJson

from pub_sub.core.PubSubExceptions import PubSubInvalidJsonException


PLACEHOLDER_START = "["
PLACEHOLDER_END = "]"


def parse_string_to_dict(string: str) -> SingleJson:
    """Parse json string to dict.

    Args:
        string: string to parse

    Raises:
        PubSubInvalidJsonException: If provided JSON string is invalid

    Returns:
        SingleJson: parsed dict
    """
    try:
        return json.loads(string)
    except Exception as err:
        raise PubSubInvalidJsonException(
            f"Unable to parse provided json. Error is: {err}"
        ) from err


def transform_template_string(template: str, event: SingleJson) -> str:
    """Transform string containing template using event data.

    Args:
        template: {str} String containing template
        event: {dict} Case event

    Returns:
        {str} Transformed string
    """
    if not template:
        return ""

    def template_has_unresolved_placeholder(
            template_: str,
            current_index: int
    ) -> bool:
        return (
            PLACEHOLDER_START in template_[current_index:]
            and PLACEHOLDER_END in template_[current_index:]
        )

    index = 0
    while template_has_unresolved_placeholder(template, index):
        partial_template = template[index:]
        start, end = (
            partial_template.find(PLACEHOLDER_START) + len(PLACEHOLDER_START),
            partial_template.find(PLACEHOLDER_END)
        )
        substring = partial_template[start:end]
        value = event.get(substring) if event.get(substring) else ""
        template = template.replace(
            f"{PLACEHOLDER_START}{substring}{PLACEHOLDER_END}",
            value,
            1,
        )
        index = index + start + len(value)

    return template


def get_default_severity(value: str) -> int:
    """Parse default severity."""
    try:
        return round(float(value))

    except (ValueError, TypeError) as e:
        raise ValueError(
            f"Invalid severity default value - {value}, please "
            "supply a valid integer."
        ) from e


def get_int_float_severity(value: str) -> int | None:
    """Parse int or float severity."""
    try:
        return value if value is None else round(float(value))

    except (ValueError, TypeError) as e:
        raise ValueError(
            f"Invalid severity value - {value}, please supply a "
            "transformation or switch to an integer or float field."
        ) from e


def get_mapped_severity(value: str, transformation: SingleJson) -> int | None:
    """Parse severity that has predefined mapping."""
    try:
        value_ = transformation.get(value)
        return value_ if value_ is None else round(float(value_))

    except (ValueError, TypeError) as e:
        raise ValueError(
            f"Invalid severity value - {value}, provided transformation is not "
            f"valid, please recheck it or switch to an integer or float field."
        ) from e


def build_severity_transformation(
        transformation: str,
) -> Callable[[str], int | None]:
    """Build severity key: transformation function mapping."""
    if transformation:
        return partial(get_mapped_severity, transformation=transformation)

    return get_int_float_severity
