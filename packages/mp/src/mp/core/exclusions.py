"""Module for lazily loading exclusion data from YAML files."""

# Copyright 2025 Google LLC
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

import pathlib
from functools import cache
from typing import Any

import yaml


@cache
def _load_exclusions_data() -> dict[str, Any]:
    """Load exclusion data from the YAML file, caching the result.

    Returns:
        A dictionary containing the exclusion data.

    """
    file_path: pathlib.Path = pathlib.Path(__file__).parent / "data" / "exclusions.yaml"
    with file_path.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def get_excluded_long_param_description_prefixes() -> set[str]:
    """Return a set of excluded long parameter description prefixes.

    Returns:
        A set of excluded long parameter description prefixes.

    """
    data = _load_exclusions_data()
    return set(data.get("excluded_long_param_description_prefixes", []))


def _build_regex_from_list(excluded_names: list[str], base_regex: str) -> str:
    """Build a regex string from a list of excluded names.

    Args:
        excluded_names: A list of strings to be excluded.
        base_regex: The base regex pattern to allow.

    Returns:
        A combined regex string.

    """
    return f"{base_regex}|" + r"|".join(excluded_names)


def get_script_display_name_regex() -> str:
    """Build and return the script display name regex.

    Returns:
        The script display name regex.

    """
    data: dict[str, Any] = _load_exclusions_data()
    excluded_names: list[str] = data.get("excluded_script_display_names_for_regex", [])
    return _build_regex_from_list(excluded_names, r"^[A-Za-z0-9-_,\s]+$")


def get_param_display_name_regex() -> str:
    """Build and return the parameter display name regex.

    Returns:
        The parameter display name regex.

    """
    data: dict[str, Any] = _load_exclusions_data()
    excluded_names: list[str] = data.get("excluded_param_display_names_for_regex", [])
    return _build_regex_from_list(excluded_names, r"^[a-zA-Z0-9-'\s]+$")


def get_script_identifier_regex() -> str:
    """Build and return the script identifier regex.

    Returns:
        The script identifier regex.

    """
    data: dict[str, Any] = _load_exclusions_data()
    excluded_names: list[str] = data.get("excluded_script_identifier_names_for_regex", [])
    return _build_regex_from_list(excluded_names, r"^[a-zA-Z0-9-_]+$")


def get_excluded_names_without_verify_ssl() -> set[str]:
    """Return a set of excluded names without verify ssl.

    Returns:
        A set of excluded names without verify ssl.

    """
    data = _load_exclusions_data()
    return set(data.get("excluded_names_without_verify_ssl", []))


def get_excluded_connector_names_without_documentation_link() -> set[str]:
    """Return a set of excluded connector names without documentation link.

    Returns:
        A set of excluded connector names without documentation link.

    """
    data = _load_exclusions_data()
    return set(data.get("excluded_connector_names_without_documentation_link", []))


def get_excluded_integrations_without_documentation_link() -> set[str]:
    """Return a set of excluded integrations without documentation link.

    Returns:
        A set of excluded integrations without documentation link.

    """
    data = _load_exclusions_data()
    return set(data.get("excluded_integrations_without_documentation_link", []))


def get_excluded_integrations_with_connectors_and_no_mapping() -> set[str]:
    """Return a set of excluded integrations with connectors and no mapping.

    Returns:
        A set of excluded integrations with connectors and no mapping.

    """
    data = _load_exclusions_data()
    return set(data.get("excluded_integrations_with_connectors_and_no_mapping", []))


def get_excluded_param_names_with_too_many_words() -> set[str]:
    """Return a set of excluded param names with too many words.

    Returns:
        A set of excluded param names with too many words.

    """
    data = _load_exclusions_data()
    return set(data.get("excluded_param_names_with_too_many_words", []))


def get_excluded_names_where_ssl_default_is_not_true() -> set[str]:
    """Return a set of excluded names where ssl default is not true.

    Returns:
        A set of excluded names where ssl default is not true.

    """
    data = _load_exclusions_data()
    return set(data.get("excluded_names_where_ssl_default_is_not_true", []))
