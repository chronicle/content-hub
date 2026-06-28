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

from TIPCommon.transformation import convert_list_to_comma_string

from sysdig_secure.core.SysdigSecureConstants import SEVERITY_PARAMETER_MAPPING


def build_events_filter(
    custom_filter_query=None,
    lowest_severity=None,
    rule_names=None,
    exclude_rule_names=False
):
    """
    Build filter to get events

    Args:
        custom_filter_query (str): custom filter query to use as filter
        lowest_severity (str): lowest severity to use in filter
        rule_names (list[str]): list of rule names to use in filter
        exclude_rule_names (bool): specifies if rule names should be excluded or no

    Returns:
        str: events filter query
    """
    if custom_filter_query:
        return custom_filter_query

    filters = [build_severity_filter(lowest_severity)]

    if rule_names:
        filters.append(build_rule_name_filter(rule_names, exclude_rule_names))

    return " and ".join(filters)


def build_severity_filter(lowest_severity: str = None) -> str:
    """
    Build severity filter

    Args:
        lowest_severity (str): lowest severity to use in filter

    Returns:
        str: severity filter query
    """
    severity_values = []
    severity_keys = list(SEVERITY_PARAMETER_MAPPING.keys())
    start_index = severity_keys.index(
        lowest_severity.casefold()
    ) if lowest_severity else 0

    for key in severity_keys[start_index:]:
        severity_values.extend(SEVERITY_PARAMETER_MAPPING[key])

    return f"severity in ({convert_list_to_comma_string(severity_values)})"


def build_rule_name_filter(
    rule_names: list[str] = None, exclude_rule_names: bool = False
) -> str:
    """
    Build rule name filter

    Args:
        rule_names (list[str]): list of rule names to use in filter
        exclude_rule_names (bool): specifies if rule names should be excluded or no

    Returns:
        str: rule name filter query
    """
    rule_names_str = [f'"{rule_name}"' for rule_name in rule_names]

    return (
        f"{'not' if exclude_rule_names else ''} "
        f"ruleName in ({convert_list_to_comma_string(rule_names_str)})"
    )


def convert_nanoseconds_to_milliseconds(unix_ns: int) -> int:
    """
    Converts unix time in nanoseconds to milliseconds

    Args:
        unix_ns (int): unix time in nanoseconds

    Returns:
        int: unix time in milliseconds
    """
    return unix_ns // 1_000_000


def convert_milliseconds_to_nanoseconds(unix_ms: int) -> int:
    """
    Converts unix time in milliseconds to nanoseconds

    Args:
        unix_ms (int): unix time in milliseconds

    Returns:
        int: unix time in nanoseconds
    """
    return unix_ms * 1_000_000
