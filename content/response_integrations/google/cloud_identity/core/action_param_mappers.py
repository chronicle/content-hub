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

# ruff: noqa: ANN401

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import yaml

if TYPE_CHECKING:
    from collections.abc import Callable
    from enum import Enum


def required() -> Callable[[Any], Any]:
    """Validate that a parameter is not None.

    Returns:
        A validation function that raises a ValueError if the input is None.

    """

    def _inner(v: Any) -> Any:
        if v is not None:
            return v
        msg = "Parameter is mandatory."
        raise ValueError(msg)

    return _inner


def non_empty() -> Callable[[Any], Any]:
    """Validate that a parameter is not empty.

    Returns:
        A validation function that raises a ValueError if the input is an empty string or list.

    """

    def _inner(v: Any) -> Any:
        if v not in ("", []):
            return v
        msg = "Parameter cannot be empty."
        raise ValueError(msg)

    return _inner


def as_type(t: type) -> Callable[[Any], Any]:
    """Cast a value to a given type.

    Args:
        t: The type to cast the value to.

    Returns:
        A function that performs the type casting.

    """

    def _inner(v: Any) -> Any:
        return t(v)

    return _inner


def parse_bool() -> Callable[[Any], Any]:
    """Parse a boolean value from a string.

    Returns:
        A function that parses a boolean from a string, raising a ValueError for invalid inputs.

    """

    def _inner(v: Any) -> Any:
        if v.lower() == "true":
            return True
        if v.lower() == "false":
            return False
        msg = f"Value {v} is not a boolean string value."
        raise ValueError(msg)

    return _inner


def as_csv(separator: str = ",") -> Callable[[Any], list[str]]:
    """Split a string into a list by a separator.

    Args:
        separator: The separator to split the string by.

    Returns:
        A function that splits a string into a list of strings.

    """

    def _inner(v: Any) -> list[str]:
        if not isinstance(v, str):
            msg = f"Value {v} is not a string."
            raise TypeError(msg)
        return [item.strip() for item in v.split(separator) if item.strip()]

    return _inner


def as_dict_from_yaml() -> Callable[[Any], dict[str, Any]]:
    """Convert a YAML string to a Python dictionary.

    Returns:
        A function that converts a YAML string to a Python dictionary.

    """

    def _inner(v: Any) -> dict[str, Any]:
        try:
            return yaml.safe_load(v)
        except yaml.YAMLError as e:
            msg = f"Invalid YAML format: {e}"
            raise ValueError(msg) from e

    return _inner


def as_dataclass_from_dict(dataclass_type: type[Any]) -> Callable[[Any], Any]:
    """Convert a dictionary to a dataclass instance.

    Args:
        dataclass_type: The type of the dataclass to convert to.

    Returns:
        A function that converts a dictionary to a dataclass instance.

    """

    def _inner(v: Any) -> Any:
        if not isinstance(v, dict):
            msg = f"Value {v} is not a dictionary."
            raise TypeError(msg)
        return dataclass_type.from_dict(v)

    return _inner


def to_lower_case() -> Callable[[Any], Any]:
    """Convert a string to lower case.

    Returns:
        A function that converts a string to lower case.

    """

    def _inner(v: Any) -> Any:
        if not isinstance(v, str):
            msg = f"Value {v} is not a string."
            raise TypeError(msg)
        return v.lower()

    return _inner


def to_upper_case() -> Callable[[Any], Any]:
    """Convert a string to upper case.

    Returns:
        A function that converts a string to upper case.

    """

    def _inner(v: Any) -> Any:
        if not isinstance(v, str):
            msg = f"Value {v} is not a string."
            raise TypeError(msg)
        return v.upper()

    return _inner


def as_ddl(enum_type: type[Enum]) -> Callable[[Any], Any]:
    """Get an enum member from a string value.

    Args:
        enum_type: The enum to get the member from.

    Returns:
        A function that converts a string to an enum member.

    """

    def _inner(v: Any) -> Any:
        try:
            if not v:
                return None
            return enum_type(v)
        except ValueError as exc:
            msg = f"Invalid value {v}. Possible values are: {[e.value for e in enum_type]}"
            raise ValueError(msg) from exc

    return _inner


def validate_max(max_value: int) -> Callable[[Any], Any]:
    """Validate that a value is not greater than a maximum value.

    Args:
        max_value: The maximum value.

    Returns:
        A validation function.

    """

    def _inner(v: Any) -> Any:
        if v > max_value:
            msg = f"Value {v} is greater than maximum value {max_value}"
            raise ValueError(msg)
        return v

    return _inner


def validate_range(min_value: Any, max_value: Any) -> Callable[[Any], Any]:
    """Validate that a value is within a given range.

    Args:
        min_value: The minimum value.
        max_value: The maximum value.

    Returns:
        A validation function.

    """

    def _inner(v: Any) -> Any:
        if not min_value <= v <= max_value:
            msg = f"Value {v} is not within the valid range [{min_value}, {max_value}]"
            raise ValueError(msg)
        return v

    return _inner


def validate_min(min_value: int) -> Callable[[Any], Any]:
    """Validate that a value is not smaller than a minimum value.

    Args:
        min_value: The minimum value.

    Returns:
        A validation function.

    """

    def _inner(v: Any) -> Any:
        if v < min_value:
            msg = f"Value {v} is smaller than minimum value {min_value}"
            raise ValueError(msg)
        return v

    return _inner


def validate_non_negative() -> Callable[[Any], Any]:
    """Validate that a value is not negative.

    Returns:
        A validation function.

    """

    def _inner(v: Any) -> Any:
        if v < 0:
            msg = f"Value {v} is negative"
            raise ValueError(msg)
        return v

    return _inner


def validate_non_positive() -> Callable[[Any], Any]:
    """Validate that a value is not positive.

    Returns:
        A validation function.

    """

    def _inner(v: Any) -> Any:
        if v > 0:
            msg = f"Value {v} is positive"
            raise ValueError(msg)
        return v

    return _inner
