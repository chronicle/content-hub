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

"""Module: [utils] defined custom functions."""
from __future__ import annotations

import re
from typing import Any

from soar_sdk.SiemplifyAction import SiemplifyAction
from TIPCommon import (
    adjust_to_csv,
    extract_configuration_param,
    get_unicode,
    none_to_default_value,
)

from .constants import (
    FILTER_KEY_VALUES,
    FILTER_STRATEGY_MAPPING,
    INTEGRATION_IDENTIFIER,
    IPV4_REGEXP,
    IP_MASKING,
)


def mask_sensitive_value(value: str) -> str:
    regex = re.compile(IPV4_REGEXP)
    if re.search(regex, value) is not None:
        return re.sub(regex, IP_MASKING, value)

    return f"{value[0]}...{value[-1]}"


def rec_mask_sensitive_values(
    data: list[Any] | dict[str, Any], sensitive_keys: list[str] | None = None
) -> list[Any] | dict[str, Any]:
    """Mask sesitive values for keys defined in sensitive_keys list argument.

    Args:
        data (dict): reponse from the api
        sensitive_keys (list, optional): mask the value for the keys define in
                                         sensitive_keys. Defaults to None.

    Returns:
        dict: masked dictionary returns.
    """
    if not isinstance(data, (list, dict)):
        return data

    sensitive_keys = none_to_default_value(sensitive_keys, [])

    if isinstance(data, list):
        return [rec_mask_sensitive_values(item, sensitive_keys) for item in data]

    for key, value in data.items():
        if isinstance(value, (list, dict)):
            data[key] = rec_mask_sensitive_values(value, sensitive_keys)

        elif key in sensitive_keys and isinstance(value, str):
            data[key] = mask_sensitive_value(value)

    return data


def filter_items(
    items: list[str, Any],
    filter_key: str | None = None,
    filter_logic: str | None = None,
    filter_value: str | None = None,
    limit: int | None = None,
) -> list[dict]:
    """Filter list of items.

    Args:
        items: {list} list of items to filter
        filter_key: {str} filter key that should be used for filtering
        filter_logic: {str} filter logic that should be applied
        filter_value: {str} filter value that should be used for filtering
        limit: {int} limit for items

    Returns:
        List: list of filtered items
    """
    filtered_key = FILTER_KEY_VALUES.get(filter_key)
    filtered_logic = FILTER_STRATEGY_MAPPING.get(filter_logic)

    if filtered_key and filtered_logic and filter_value:
        items = [
            item
            for item in items
            if filtered_logic(getattr(item, filtered_key), filter_value)
        ]

    return items[:limit] if limit is not None else items


def construct_ordered_csv(list_of_dicts):
    """Constructs a CSV from a list of dictionaries.

    Args:
        list_of_dicts (list[dict]): The list of dictionaries to add to the CSV.

    Returns:
        list[str]: The CSV formatted list.
    """
    csv_output = []
    if not list_of_dicts:
        return csv_output
    headers = list(list_of_dicts[0].keys())
    unicode_headers = []
    for header in headers:
        header = adjust_to_csv(header)
        header = get_unicode(header)
        unicode_headers.append(header)
    csv_output.append(",".join(unicode_headers))
    for result in list_of_dicts:
        csv_row = []
        for header in headers:
            cell_value = result.get(header)
            cell_value = adjust_to_csv(cell_value)
            cell_value = get_unicode(cell_value)

            # Replace problematic commas
            cell_value = cell_value.replace(",", " ")
            # Append values to the row
            csv_row.append(cell_value)
        # Append row to the output
        csv_output.append(",".join(csv_row))
    return csv_output


def get_configuration_params(
    siemplify_action_instance: SiemplifyAction,
) -> tuple[str, str, str, str, bool]:
    """Getting Confluence Integration Configuration Parameters.

    Args:
        siemplify_action_instance: SiemplifyAction instance object.

    Returns:
        tuple: str, str, str, str, bool
    """

    api_root = extract_configuration_param(
        siemplify_action_instance,
        provider_name=INTEGRATION_IDENTIFIER,
        param_name="Api Root",
        is_mandatory=True,
        print_value=True,
    )
    username = extract_configuration_param(
        siemplify_action_instance,
        provider_name=INTEGRATION_IDENTIFIER,
        param_name="Username",
        is_mandatory=False,
        print_value=True,
    )
    password = extract_configuration_param(
        siemplify_action_instance,
        provider_name=INTEGRATION_IDENTIFIER,
        param_name="Password",
        is_mandatory=False,
        print_value=False,
    )
    api_token = extract_configuration_param(
        siemplify_action_instance,
        provider_name=INTEGRATION_IDENTIFIER,
        param_name="Api Token",
        is_mandatory=False,
        print_value=False,
    )
    verify_ssl = extract_configuration_param(
        siemplify_action_instance,
        provider_name=INTEGRATION_IDENTIFIER,
        param_name="Verify SSL",
        default_value=False,
        input_type=bool,
        print_value=True,
    )
    return api_root, username, password, api_token, verify_ssl
