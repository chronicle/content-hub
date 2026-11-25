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

import copy
import datetime
import json
import os
from typing import Any, Dict, List

import requests
from soar_sdk.SiemplifyUtils import (
    convert_datetime_to_unix_time,
    convert_string_to_unix_time,
    unix_now,
    utc_now,
)
from TIPCommon import validate_map_file

from EnvironmentCommon import EnvironmentHandle
from .TenableIOExceptions import TenableIOException
from .constants import FINISHED_STATUS

# Move to TIPCommon
STORED_IDS_LIMIT = 10000
TIMEOUT_THRESHOLD = 0.9
WHITELIST_FILTER = 1
BLACKLIST_FILTER = 2
UNIX_FORMAT = 1
DATETIME_FORMAT = 2
GLOBAL_TIMEOUT_THRESHOLD_IN_MIN = 1


def is_async_action_global_timeout_approaching(siemplify, start_time):
    return (
        siemplify.execution_deadline_unix_time_ms - start_time
        < GLOBAL_TIMEOUT_THRESHOLD_IN_MIN * 60
    )


def validate_response(response, error_msg="An error occurred"):
    """
    Validate response
    :param response: {requests.Response} The response to validate
    :param error_msg: {unicode} Default message to display on error
    """
    try:
        response.raise_for_status()
    except requests.HTTPError as error:
        try:
            response.json()
        except Exception:
            raise TenableIOException(f"{error_msg}: {error} {error.response.content}")

        raise TenableIOException(
            f"{error_msg}: {error} {response.json().get('message') or response.content}"
        )


def get_entity_original_identifier(entity):
    """
    Helper function for getting entity original identifier
    :param entity: entity from which function will get original identifier
    :return: {str} original identifier
    """
    return entity.additional_properties.get("OriginalIdentifier", entity.identifier)


def convert_comma_separated_to_list(comma_separated):
    """
    Convert comma-separated string to list
    :param comma_separated: String with comma-separated values
    :return: List of values
    """
    return (
        [item.strip() for item in comma_separated.split(",")] if comma_separated else []
    )


def convert_list_to_comma_string(values_list):
    """
    Convert list to comma-separated string
    :param values_list: List of values
    :return: String with comma-separated values
    """
    return (
        ", ".join(str(v) for v in values_list)
        if values_list and isinstance(values_list, list)
        else values_list
    )


def convert_list_to_semicolon_string(values_list):
    """
    Convert list to semicolon-separated string
    :param values_list: List of values
    :return: String with semicolon-separated values
    """
    return (
        "; ".join(str(v) for v in values_list)
        if values_list and isinstance(values_list, list)
        else values_list
    )


def read_pending_export(siemplify, export_file_name="pending_export.json"):
    """
    Read pending export from file
    :param siemplify: {Siemplify} Siemplify object.
    :param export_file_name: {str} The name of the file
    :return: {list} List of ids
    """
    export_file_path = os.path.join(siemplify.run_folder, export_file_name)

    if not os.path.exists(export_file_path):
        return {}

    try:
        with open(export_file_path, "r") as f:
            return json.loads(f.read())
    except Exception as e:
        siemplify.LOGGER.error(f"Unable to read pending export file: {e}")
        siemplify.LOGGER.exception(e)
        return {}


def write_pending_export(
    siemplify, export_data, export_file_name="pending_export.json"
):
    """
    Write pending export to the file
    :param siemplify: {Siemplify} Siemplify object.
    :param export_data: {dict} The export data to write to the file
    :param export_file_name: {str} The name of the file.
    :return: {bool}
    """

    if export_data.get("status") == FINISHED_STATUS:
        export_data["chunks_available"] = export_data["chunks_available"][1:]

    try:
        export_file_path = os.path.join(siemplify.run_folder, export_file_name)

        if not os.path.exists(os.path.dirname(export_file_path)):
            os.makedirs(os.path.dirname(export_file_path))

        with open(export_file_path, "w") as f:
            try:
                if export_data.get("status") == FINISHED_STATUS:
                    (
                        f.write(json.dumps(export_data))
                        if export_data.get("chunks_available", [])
                        else f.write("{}")
                    )
                else:
                    f.write(json.dumps(export_data))
            except:
                f.write("{}")
                raise

        siemplify.LOGGER.info("Export data was written to the file")
        return True

    except Exception as e:
        siemplify.LOGGER.error(f"Failed writing Export data to the file, ERROR: {e}")
        siemplify.LOGGER.exception(e)
        return False


# Move to TIPCommon
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


# Move to TIPCommon
def get_last_success_time(
    siemplify,
    offset_with_metric,
    time_format=DATETIME_FORMAT,
    print_value=True,
    date_time_format=None,
):
    """
    Get last success time datetime
    :param siemplify: {siemplify} Siemplify object
    :param offset_with_metric: {dict} metric and value. Ex {"hours": 1}
    :param time_format: {int} The format of the output time. Ex DATETIME, UNIX
    :param print_value: {bool} Whether log the value or not
    :param date_time_format: {str} Datetime format to return data
    :return: {time} If first run, return current time minus offset time, else return timestamp from file
    """
    last_run_timestamp = siemplify.fetch_timestamp(datetime_format=True)
    offset = datetime.timedelta(**offset_with_metric)
    current_time = utc_now()
    # Check if first run
    raw_datetime = (
        current_time - offset
        if current_time - last_run_timestamp > offset
        else last_run_timestamp
    )
    unix_result = convert_datetime_to_unix_time(raw_datetime)
    datetime_result = (
        raw_datetime
        if not date_time_format
        else raw_datetime.strftime(date_time_format)
    )

    if print_value:
        siemplify.LOGGER.info(
            f"Last success time. Date time:{datetime_result}. Unix:{unix_result}"
        )

    return unix_result if time_format == UNIX_FORMAT else datetime_result


# Move to TIPCommon
def get_environment_common(
    siemplify, environment_field_name, environment_regex_pattern, map_file="map.json"
):
    """
    Get environment common
    :param siemplify: {siemplify} Siemplify object
    :param environment_field_name: {str} The environment field name
    :param environment_regex_pattern: {str} The environment regex pattern
    :param map_file: {str} The map file
    :return: {EnvironmentHandle}
    """
    map_file_path = os.path.join(siemplify.run_folder, map_file)
    validate_map_file(siemplify, map_file_path)
    return EnvironmentHandle(
        map_file_path,
        siemplify.LOGGER,
        environment_field_name,
        environment_regex_pattern,
        siemplify.context.connector_info.environment,
    )


def filter_old_alerts(logger, alerts, existing_ids, id_key="id"):
    """
    Filter alerts that were already processed
    :param logger: {SiemplifyLogger} Siemplify logger
    :param alerts: {list} List of Alert objects
    :param existing_ids: {list} List of ids to filter
    :param id_key: {str} The key of identifier
    :return: {list} List of filtered Alert objects
    """
    filtered_alerts = []

    for alert in alerts:
        id = getattr(alert, id_key)

        if id not in existing_ids.get(alert.asset_id, []):
            filtered_alerts.append(alert)
        else:
            logger.info(
                f"The vulnerability {id} skipped since it has been fetched before"
            )

    return filtered_alerts


def read_ids(siemplify, ids_file_name="ids.json"):
    """
    Read existing alerts IDs from ids file (from last 24h only)
    :param siemplify: {Siemplify} Siemplify object.
    :param ids_file_name: {str} The name of the ids file
    :return: {list} List of ids
    """
    ids_file_path = os.path.join(siemplify.run_folder, ids_file_name)

    if not os.path.exists(ids_file_path):
        return {}

    try:
        with open(ids_file_path, "r") as f:
            return json.loads(f.read())
    except Exception as e:
        siemplify.LOGGER.error(f"Unable to read ids file: {e}")
        siemplify.LOGGER.exception(e)
        return {}


def write_ids(siemplify, ids, ids_file_name="ids.json"):
    """
    Write ids to the ids file
    :param siemplify: {Siemplify} Siemplify object.
    :param ids: {list} The ids to write to the file
    :param ids_file_name: {str} The name of the ids file.
    :return: {bool}
    """
    for key, value in ids.items():
        ids[key] = value[-STORED_IDS_LIMIT:]

    try:
        ids_file_path = os.path.join(siemplify.run_folder, ids_file_name)

        if not os.path.exists(os.path.dirname(ids_file_path)):
            os.makedirs(os.path.dirname(ids_file_path))

        with open(ids_file_path, "w") as f:
            try:
                for chunk in json.JSONEncoder().iterencode(ids):
                    f.write(chunk)
            except:
                # Move seeker to start of the file
                f.seek(0)
                # Empty the content of the file (the partially written content that was written before the exception)
                f.truncate()
                # Write an empty dict to the events data file
                f.write("{}")
                raise

        siemplify.LOGGER.info(f"Write ids. Total hosts={len(ids)}")
        return True

    except Exception as e:
        siemplify.LOGGER.error(f"Failed writing IDs to IDs file, ERROR: {e}")
        siemplify.LOGGER.exception(e)
        return False


def _get_asset_identifiers(asset: Any) -> set[str]:
    """
    Extracts all possible string identifiers from an asset object.
    Args:
        asset (Any): A Tenable asset data object.
    Returns:
        set[str]: A set of all found identifiers (IPs, hostnames, etc.).
    """
    identifiers = set()

    # Add IP addresses
    for ip in asset.ipv4:
        identifiers.add(ip)
    for ip in asset.ipv6:
        identifiers.add(ip)

    # Add FQDNs and their short forms
    for fqdn in asset.fqdn:
        fqdn_lower = fqdn.lower()
        identifiers.add(fqdn_lower)
        identifiers.add(fqdn_lower.split(".")[0])

    # Add hostnames and their short forms
    for hostname in asset.hostname:
        hostname_lower = hostname.lower()
        identifiers.add(hostname_lower)
        identifiers.add(hostname_lower.split(".")[0])

    # Add agent names
    for agent_name in asset.agent_names:
        identifiers.add(agent_name.lower())

    # Add NetBIOS names
    for netbios in asset.netbios_name:
        identifiers.add(netbios.lower())

    return identifiers


def build_identifier_to_asset_map(all_assets: List[Any]) -> Dict[str, Any]:
    """
    Build a lookup map from various asset identifiers to the full asset object.
    Args:
        all_assets (List[Any]): A list of all asset objects from Tenable.io.
    Returns:
        Dict[str, Any]: A map of identifiers to the corresponding asset object.
    """
    asset_map = {}
    for asset in all_assets:
        identifiers = _get_asset_identifiers(asset)
        for identifier in identifiers:
            if identifier not in asset_map:
                asset_map[identifier] = asset
    return asset_map


def build_identifier_to_ip_map(all_assets: List[Any]) -> Dict[str, str]:
    """
    Build a lookup map from various asset identifiers to a primary IP address.
    Args:
        all_assets (List[Any]): A list of all asset objects from Tenable.io.
    Returns:
        Dict[str, str]: A map of identifiers to the asset's primary IPv4 address.
    """
    ip_map = {}
    for asset in all_assets:
        if not asset.ipv4:
            continue

        primary_ip = asset.ipv4[0]
        identifiers = _get_asset_identifiers(asset)

        for identifier in identifiers:
            if identifier not in ip_map:
                ip_map[identifier] = primary_ip
    return ip_map


# Move to TIPCommon
def is_overflowed(siemplify, alert_info, is_test_run):
    """
    Check if overflowed
    :param siemplify: {Siemplify} Siemplify object.
    :param alert_info: {AlertInfo}
    :param is_test_run: {bool} Whether test run or not.
    :return: {bool}
    """
    try:
        return siemplify.is_overflowed_alert(
            environment=alert_info.environment,
            alert_identifier=alert_info.ticket_id,
            alert_name=alert_info.rule_generator,
            product=alert_info.device_product,
        )

    except Exception as e:
        siemplify.LOGGER.error(f"Error validation connector overflow, ERROR: {e}")
        siemplify.LOGGER.exception(e)

        if is_test_run:
            raise

    return False


# Move to TIPCommon
def save_timestamp(
    siemplify,
    alerts,
    timestamp_key="timestamp",
    incrementation_value=0,
    log_timestamp=True,
):
    """
    Save last timestamp for given alerts
    :param siemplify: {Siemplify} Siemplify object
    :param alerts: {list} The list of alerts to find the last timestamp
    :param timestamp_key: {str} key for getting timestamp from alert
    :param incrementation_value: {int} The value to increment last timestamp by milliseconds
    :param log_timestamp: {bool} Whether log timestamp or not
    :return: {bool} Is timestamp updated
    """
    if not alerts:
        siemplify.LOGGER.info("Timestamp is not updated since no alerts fetched")
        return False

    alerts = sorted(alerts, key=lambda alert: getattr(alert, timestamp_key))
    last_timestamp = (
        convert_string_to_unix_time(getattr(alerts[-1], timestamp_key))
        + incrementation_value
    )

    if log_timestamp:
        siemplify.LOGGER.info(f"Last timestamp is: {last_timestamp}")

    siemplify.save_timestamp(new_timestamp=last_timestamp)
    return True


def create_whitelist_filter(
    siemplify, whitelist_as_a_blacklist, plugin_families, whitelist=None
):
    # whitelist filter
    whitelist = whitelist or siemplify.whitelist
    whitelist_filter_type = (
        BLACKLIST_FILTER if whitelist_as_a_blacklist else WHITELIST_FILTER
    )
    acceptable_plugin_families = copy.deepcopy(plugin_families)
    if whitelist:
        for value in plugin_families:
            if whitelist_filter_type == BLACKLIST_FILTER and value in whitelist:
                siemplify.LOGGER.info(f"'{value}' did not pass blacklist filter.")
                acceptable_plugin_families.remove(value)

            if whitelist_filter_type == WHITELIST_FILTER and value not in whitelist:
                siemplify.LOGGER.info(f"'{value}' did not pass whitelist filter.")
                acceptable_plugin_families.remove(value)

    return acceptable_plugin_families
