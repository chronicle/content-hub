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
import math


from .constants import (
    CONFIGURATION_DATA,
    CUSTOM_CONFIGURATION_FILE_NAME,
    CUSTOM_MAPPING_CONFIGURATION,
    DEFAULT_SEVERITY_VALUE,
    SEVERITY_CUSTOM_KEY_NAME,
)

from TIPCommon.smp_io import read_content, read_ids, write_content


def load_custom_severity_configuration(
    siemplify, severity_field_name, file_path=CUSTOM_CONFIGURATION_FILE_NAME
):
    # pylint: disable=global-statement
    """Load custom severity mapping configuration from a file.

    This function loads severity mapping configurations from a specified file,
    updating global variables for default severity and custom mappings.

    Args:
        siemplify: The Siemplify object for file operations.
        severity_field_name (str): The name of the severity field to load.
        file_path (str, optional): The path to the configuration file.
            Defaults to CUSTOM_CONFIGURATION_FILE_NAME.
    """
    global DEFAULT_SEVERITY_VALUE
    global CUSTOM_MAPPING_CONFIGURATION
    global CONFIGURATION_DATA

    conf_data = read_content(
        siemplify, file_name=file_path, db_key=SEVERITY_CUSTOM_KEY_NAME
    )
    DEFAULT_SEVERITY_VALUE = conf_data.get("Default", DEFAULT_SEVERITY_VALUE)
    CUSTOM_MAPPING_CONFIGURATION = conf_data.get(
        severity_field_name, CUSTOM_MAPPING_CONFIGURATION
    )
    conf_data = {"Default": DEFAULT_SEVERITY_VALUE}
    if severity_field_name:
        conf_data[severity_field_name] = CUSTOM_MAPPING_CONFIGURATION
    CONFIGURATION_DATA = conf_data
    write_content(
        siemplify, conf_data, file_name=file_path, db_key=SEVERITY_CUSTOM_KEY_NAME
    )


def map_severity_value(severity_field_name, severity_value):
    """Map a severity value to a Chronicle SOAR priority score.

    Args:
        severity_field_name (str): The name of the severity field.
        severity_value (Union[float, str]): The severity value to map.

    Returns:
        int: The mapped Chronicle SOAR priority score, clamped between 0 and 100.
            Returns DEFAULT_SEVERITY_VALUE if `severity_field_name` is None.
    """
    if severity_field_name:
        severity_score = DEFAULT_SEVERITY_VALUE
        try:
            severity_value = float(severity_value)
        except (ValueError, TypeError):
            pass
        if isinstance(severity_value, float):
            severity_score = math.ceil(severity_value)
        elif isinstance(severity_value, str):
            severity_dict = CONFIGURATION_DATA.get(severity_field_name)
            if severity_dict:
                severity_score = severity_dict.get(
                    severity_value, DEFAULT_SEVERITY_VALUE
                )

        if severity_score > 100:
            return 100
        if severity_score < 0:
            return -1
        return int(severity_score)
    return DEFAULT_SEVERITY_VALUE


def get_field_value(flat_alert, field_name, default_value=None):
    """Get the value from a flattened alert using various field name notations.

    This function attempts to retrieve a field's value from a flattened alert
    using common OpenSearch/Elasticsearch field notations (e.g., `host.name`,
    `_source_host_name`, `host_name`).

    Args:
        flat_alert (dict): A flattened OpenSearch/Elasticsearch alert dictionary.
        field_name (str): The name of the field to retrieve.
        default_value (Any, optional): The value to return if the field is not found.
            Defaults to None.

    Returns:
        Any: The value of the field, or `default_value`.
    """
    if field_name is None:
        return default_value

    try:
        return flat_alert[field_name]
    except KeyError:
        try:
            return flat_alert[f"_source_{field_name}"]
        except KeyError:
            try:
                return flat_alert[f"_source_{field_name.replace('.', '_')}"]
            except KeyError:
                if default_value is not None:
                    return default_value
                raise


def read_and_repair_existing_ids(siemplify) -> list:
    """Read existing ids and convert them to list, if it is a dict.
    This is needed to avoid regressions.

    Args:
        siemplify: (SiemplifyConnectorExecution)

    """
    existing_ids_data = read_ids(siemplify)

    if isinstance(existing_ids_data, dict):
        return list(existing_ids_data.keys())

    return existing_ids_data
