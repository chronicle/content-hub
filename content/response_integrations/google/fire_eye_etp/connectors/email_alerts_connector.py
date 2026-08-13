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


"""Email Alerts Connector for FireEye ETP integration."""

from __future__ import annotations

import sys
import uuid
from datetime import timedelta
from typing import TYPE_CHECKING, Any

import arrow
from EnvironmentCommon import GetEnvironmentCommonFactory
from soar_sdk.SiemplifyConnectors import SiemplifyConnectorExecution
from soar_sdk.SiemplifyConnectorsDataModel import AlertInfo
from soar_sdk.SiemplifyUtils import (
    convert_unixtime_to_datetime,
    output_handler,
    unix_now,
    utc_now,
)
from TIPCommon.extraction import extract_connector_param
from TIPCommon.filters import filter_old_alerts
from TIPCommon.smp_io import read_ids, write_ids
from TIPCommon.smp_time import is_approaching_timeout, validate_timestamp
from TIPCommon.transformation import dict_to_flat
from TIPCommon.utils import is_overflowed

from ..core.fire_eye_etp_constants import (
    ACCEPTABLE_TIME_INTERVAL_IN_MINUTES,
    ALERT_ID_FIELD,
    ALERT_NAME,
    ALERTS_CONNECTOR_NAME,
    BLACKLIST_FILTER,
    DEFAULT_TIME_FRAME,
    DEVICE_PRODUCT,
    DEVICE_VENDOR,
    PRINT_TIME_FORMAT,
    WHITELIST_FILTER,
)
from ..core.fire_eye_etp_manager import FireEyeETPConfig, FireEyeETPManager

if TYPE_CHECKING:
    from ..core.datamodels import Alert

MIN_REQUIRED_ARGS = 2


def filter_recent_alerts(
    siemplify: SiemplifyConnectorExecution,
    alert_groups: list[list[Alert]],
    max_minutes_backwards: int = ACCEPTABLE_TIME_INTERVAL_IN_MINUTES,
) -> list[list[Alert]]:
    """Filter alert groups that occurred too recently.

    Args:
        siemplify: Siemplify logger and execution context.
        alert_groups: List of grouped alerts.
        max_minutes_backwards: Maximum minutes backwards to filter.

    Returns:
        List of filtered alert groups.

    """
    filtered_groups: list[list[Alert]] = []

    for group in alert_groups:
        if group[0].occurred_time_unix < arrow.utcnow().shift(minutes=-max_minutes_backwards).timestamp * 1000:
            filtered_groups.append(group)

        else:
            siemplify.LOGGER.info(
                f"Alert group with email ID {group[0].etp_message_id} did not "
                f"pass time filter. Earliest Alert in the group occurred in the "
                f"last {max_minutes_backwards} minutes."
            )

    return filtered_groups


def pass_whitelist_filter(
    alert_group: list[Alert],
    whitelist: list[str],
    whitelist_filter_type: str,
) -> bool:
    """Check if the alert group passes the whitelist/blacklist filter.

    Args:
        alert_group: Group of alerts.
        whitelist: List of whitelisted/blacklisted alert names.
        whitelist_filter_type: Filter type (whitelist or blacklist).

    Returns:
        True if it passes the filter, False otherwise.

    """
    if whitelist:
        # Check if the alert name is in the whitelist/blacklist
        alert_name = alert_group[0].name
        if whitelist_filter_type == WHITELIST_FILTER:
            return alert_name in whitelist
        if whitelist_filter_type == BLACKLIST_FILTER:
            return alert_name not in whitelist

    return True


def group_alerts(fetched_alerts: list[Alert]) -> list[list[Alert]]:
    """Group alerts by their ETP message ID.

    Args:
        fetched_alerts: List of fetched alerts.

    Returns:
        List of grouped alerts sorted by earliest occurrence.

    """
    groups: dict[str, list[Alert]] = {}
    for alert in fetched_alerts:
        groups.setdefault(alert.etp_message_id, []).append(alert)
    grouped_alerts: list[list[Alert]] = list(groups.values())

    # Sort groups by the occurred time of the earliest alert in each group.
    return sorted(
        grouped_alerts,
        key=lambda alert_group: min(alert_group, key=lambda alert: alert.occurred_time_unix).occurred_time_unix,
    )


def calculate_priority(alerts_group: list[Alert]) -> int:
    """Calculate the maximum priority in an alerts group.

    Args:
        alerts_group: Group of alerts.

    Returns:
        The maximum priority value.

    """
    return max(alert.priority for alert in alerts_group)


def create_alert_info(
    environment: Any,  # noqa: ANN401
    alerts_group: list[Alert],
) -> AlertInfo:
    """Create a Siemplify AlertInfo object from a group of alerts.

    Args:
        environment: Environment common manager.
        alerts_group: Group of alerts.

    Returns:
        The constructed AlertInfo object.

    """
    sorted_alerts_group: list[Alert] = sorted(alerts_group, key=lambda alert: alert.occurred_time_unix)

    alert_info: AlertInfo = AlertInfo()
    alert_info.display_id = str(uuid.uuid4())
    alert_info.ticket_id = sorted_alerts_group[0].id
    alert_info.name = ALERT_NAME
    alert_info.rule_generator = sorted_alerts_group[0].name
    alert_info.priority = calculate_priority(alerts_group)
    alert_info.start_time = sorted_alerts_group[0].occurred_time_unix
    alert_info.end_time = sorted_alerts_group[-1].occurred_time_unix

    alert_info.device_vendor = DEVICE_VENDOR
    alert_info.device_product = DEVICE_PRODUCT

    events: list[dict[str, Any]] = []
    for alert in sorted_alerts_group:
        events.extend(alert.events)

    events.extend(sorted_alerts_group[0].recipient_events)

    alert_info.events = [dict_to_flat(event) for event in events]
    alert_info.environment = environment.get_environment(sorted_alerts_group[0].raw_data)

    return alert_info


def process_single_alert_group(
    siemplify: SiemplifyConnectorExecution,
    etp_manager: FireEyeETPManager,
    alert_group: list[Alert],
    params: dict[str, Any],
    context: dict[str, Any],
) -> AlertInfo | None:
    """Process a single alert group and return AlertInfo if successful.

    Args:
        siemplify: The Siemplify connector execution object.
        etp_manager: The FireEye ETP manager.
        alert_group: The alert group to process.
        params: The integration parameters.
        context: The execution context.

    Returns:
        The constructed AlertInfo object, or None if skipped/failed.

    """
    existing_ids = context["existing_ids"]
    is_test_run = context["is_test_run"]
    whitelist = siemplify.whitelist

    whitelist_as_a_blacklist = params["whitelist_as_a_blacklist"]
    whitelist_filter_type = BLACKLIST_FILTER if whitelist_as_a_blacklist else WHITELIST_FILTER

    siemplify.LOGGER.info(f"Processing alert group {alert_group[0].etp_message_id}")
    siemplify.LOGGER.info(f"There are {len(alert_group)} alerts in this group")

    if not pass_whitelist_filter(alert_group, whitelist, whitelist_filter_type):
        siemplify.LOGGER.info(f"Alert group {alert_group[0].name} did not pass filters skipping....")
        existing_ids.extend([alert.id for alert in alert_group])
        return None

    context["processed_alerts"].extend(alert_group)

    detailed_alert_group: list[Alert] = []
    siemplify.LOGGER.info(f"Fetching alert details for alert group {alert_group[0].etp_message_id}")
    for alert in alert_group:
        detailed_alert: Alert = etp_manager.get_alert_details(
            alert_id=alert.id, timezone_offset=params["server_timezone"]
        )
        detailed_alert_group.append(detailed_alert)

    siemplify.LOGGER.info(f"Creating AlertInfo for alert group {alert_group[0].etp_message_id}")
    environment_common: Any = GetEnvironmentCommonFactory.create_environment_manager(
        siemplify,
        environment_field_name=params["environment_field_name"],
        environment_regex_pattern=params["environment_regex_pattern"],
    )
    alert_info: AlertInfo = create_alert_info(environment_common, detailed_alert_group)

    siemplify.LOGGER.info(f"Finished creating AlertInfo for alert group {alert_group[0].etp_message_id}")

    if is_overflowed(siemplify, alert_info, is_test_run):
        siemplify.LOGGER.info(
            f"{alert_info.name}-{alert_info.ticket_id}-"
            f"{alert_info.environment}-{alert_info.device_product} "
            f"found as overflow alert. Skipping."
        )
        existing_ids.extend([alert.id for alert in alert_group])
        return None

    existing_ids.extend([alert.id for alert in alert_group])
    siemplify.LOGGER.info(f"Finished processing. Alert group {alert_group[0].etp_message_id} was created.")
    return alert_info


def process_alert_groups(
    siemplify: SiemplifyConnectorExecution,
    etp_manager: FireEyeETPManager,
    alert_groups: list[list[Alert]],
    params: dict[str, Any],
    context: dict[str, Any],
) -> list[AlertInfo]:
    """Process a list of alert groups and return created AlertInfo.

    Args:
        siemplify: The Siemplify connector execution object.
        etp_manager: The FireEye ETP manager.
        alert_groups: The alert groups to process.
        params: The integration parameters.
        context: The execution context.

    Returns:
        A list of constructed AlertInfo objects.

    """
    alerts: list[AlertInfo] = []
    connector_starting_time = context["connector_starting_time"]
    python_process_timeout = params["python_process_timeout"]

    for alert_group in alert_groups:
        if is_approaching_timeout(connector_starting_time, python_process_timeout):
            siemplify.LOGGER.info("Timeout is approaching. Connector will gracefully exit.")
            break

        try:
            alert_info = process_single_alert_group(siemplify, etp_manager, alert_group, params, context)
            if alert_info:
                alerts.append(alert_info)

        except Exception:
            siemplify.LOGGER.exception(f"Failed to process alert group {alert_group[0].etp_message_id}")
            if context["is_test_run"]:
                raise

    return alerts


def update_connector_timestamp(
    siemplify: SiemplifyConnectorExecution,
    *,
    filtered_alerts: list[Alert],
    processed_alerts: list[Alert],
    fetched_alerts: list[Alert],
) -> None:
    """Update the connector timestamp based on processed or fetched alerts.

    Args:
        siemplify: The Siemplify connector execution object.
        filtered_alerts: The list of new alerts after filtering out existing IDs.
        processed_alerts: The list of successfully processed alerts.
        fetched_alerts: The list of all fetched alerts in this cycle.

    """
    if filtered_alerts:
        if processed_alerts:
            new_timestamp: int = min(processed_alerts, key=lambda alert: alert.occurred_time_unix).occurred_time_unix
            siemplify.save_timestamp(new_timestamp=new_timestamp)
            siemplify.LOGGER.info(
                f"New timestamp "
                f"{convert_unixtime_to_datetime(new_timestamp).strftime(PRINT_TIME_FORMAT)} "
                f"has been saved"
            )

    elif fetched_alerts:
        new_timestamp = max(fetched_alerts, key=lambda alert: alert.occurred_time_unix).occurred_time_unix
        siemplify.save_timestamp(new_timestamp=new_timestamp)
        siemplify.LOGGER.info(
            f"New timestamp {convert_unixtime_to_datetime(new_timestamp).strftime(PRINT_TIME_FORMAT)} has been saved"
        )
    else:
        siemplify.LOGGER.info("No alerts were fetched. Timestamp won't be updated.")


def run_connector_cycle(
    siemplify: SiemplifyConnectorExecution,
    params: dict[str, Any],
    context: dict[str, Any],
) -> tuple[list[AlertInfo], list[Alert], list[Alert]]:
    """Run the main connector cycle (fetch, filter, process) and return results.

    Args:
        siemplify: The Siemplify connector execution object.
        params: The integration parameters.
        context: The execution context.

    Returns:
        A tuple containing:
            - A list of constructed AlertInfo objects.
            - A list of filtered new alerts.
            - A list of all fetched alerts.

    """
    is_test_run = context["is_test_run"]

    last_success_time_datetime = validate_timestamp(
        utc_now() - timedelta(hours=params["hours_backwards"])
        if is_test_run
        else siemplify.fetch_timestamp(datetime_format=True),
        params["hours_backwards"],
    )

    siemplify.LOGGER.info(f"Last success time: {last_success_time_datetime.strftime(PRINT_TIME_FORMAT)}")

    siemplify.LOGGER.info("Reading already existing alerts ids...")
    existing_ids = read_ids(siemplify)
    context["existing_ids"] = existing_ids
    siemplify.LOGGER.info(f"Found {len(existing_ids)} existing ids in ids.json")

    config = FireEyeETPConfig(
        api_root=params["api_root"],
        client_id=params["client_id"],
        client_secret=params["client_secret"],
        api_key=params["api_key"],
        verify_ssl=params["verify_ssl"],
    )
    etp_manager = FireEyeETPManager(
        config=config,
        siemplify_logger=siemplify.LOGGER,
    )

    siemplify.LOGGER.info("Fetching alerts...")
    fetched_alerts = etp_manager.get_alerts(
        start_time=last_success_time_datetime,
        timezone_offset=params["server_timezone"],
    )
    siemplify.LOGGER.info(f"Fetched {len(fetched_alerts)} alerts")

    siemplify.LOGGER.info("Filtering already processed alerts")
    filtered_alerts = filter_old_alerts(
        siemplify=siemplify,
        alerts=fetched_alerts,
        existing_ids=existing_ids,
        id_key=ALERT_ID_FIELD,
    )
    siemplify.LOGGER.info(f"Found {len(filtered_alerts)} new alerts")

    siemplify.LOGGER.info("Grouping alerts.")
    grouped_alerts = group_alerts(filtered_alerts)
    siemplify.LOGGER.info(f"Grouped into {len(grouped_alerts)} alert group based on email id")

    siemplify.LOGGER.info("Filtering too recent alerts")
    filtered_recent_alerts = filter_recent_alerts(siemplify, grouped_alerts, ACCEPTABLE_TIME_INTERVAL_IN_MINUTES)
    siemplify.LOGGER.info(f"Filtered to {len(filtered_recent_alerts)} alert groups")

    if is_test_run:
        siemplify.LOGGER.info("This is a TEST run. Only 1 alert group will be processed.")
        filtered_recent_alerts = filtered_recent_alerts[:1]

    alerts = process_alert_groups(siemplify, etp_manager, filtered_recent_alerts, params, context)

    return alerts, filtered_alerts, fetched_alerts


@output_handler
def main(*, is_test_run: bool) -> None:
    """Execute the Email Alerts Connector.

    Args:
        is_test_run: Whether this is a test run or not.

    Raises:
        ValueError: If neither client ID/secret nor API key is provided.

    """
    connector_starting_time: int = unix_now()
    siemplify: SiemplifyConnectorExecution = SiemplifyConnectorExecution()
    siemplify.script_name = ALERTS_CONNECTOR_NAME

    if is_test_run:
        siemplify.LOGGER.info('***** This is an "IDE Play Button" "Run Connector once" test run ******')

    siemplify.LOGGER.info("==================== Main - Param Init ====================")

    # Extract all parameters into a dictionary to limit local variables count (PLR0914)
    params = {
        "api_root": extract_connector_param(siemplify, param_name="API Root", is_mandatory=True, print_value=True),
        "api_key": extract_connector_param(siemplify, param_name="API Key", is_mandatory=False, print_value=False),
        "client_id": extract_connector_param(siemplify, param_name="Client ID", is_mandatory=False, print_value=False),
        "client_secret": extract_connector_param(
            siemplify, param_name="Client Secret", is_mandatory=False, print_value=False
        ),
        "verify_ssl": extract_connector_param(
            siemplify,
            param_name="Verify SSL",
            default_value=False,
            input_type=bool,
            is_mandatory=True,
            print_value=True,
        ),
        "environment_field_name": extract_connector_param(
            siemplify,
            param_name="Environment Field Name",
            default_value="",
            print_value=True,
        ),
        "environment_regex_pattern": extract_connector_param(
            siemplify,
            param_name="Environment Regex Pattern",
            default_value=".*",
            print_value=True,
        ),
        "hours_backwards": extract_connector_param(
            siemplify,
            param_name="Fetch Max Hours Backwards",
            input_type=int,
            default_value=DEFAULT_TIME_FRAME,
            print_value=True,
        ),
        "whitelist_as_a_blacklist": extract_connector_param(
            siemplify,
            "Use whitelist as a blacklist",
            is_mandatory=True,
            input_type=bool,
            print_value=True,
        ),
        "python_process_timeout": extract_connector_param(
            siemplify,
            param_name="PythonProcessTimeout",
            input_type=int,
            is_mandatory=True,
            print_value=True,
        ),
        "server_timezone": extract_connector_param(
            siemplify, param_name="Timezone", default_value="0", print_value=True
        ),
    }

    siemplify.LOGGER.info("------------------- Main - Started -------------------")

    # Validate parameters before try block to avoid TRY301 (raise within try)
    if not (params["api_key"] or (params["client_id"] and params["client_secret"])):
        msg = "Either Client ID and Client Secret, or API Key (legacy) must be provided."
        raise ValueError(msg)

    context = {
        "connector_starting_time": connector_starting_time,
        "is_test_run": is_test_run,
        "existing_ids": [],
        "processed_alerts": [],
    }

    try:
        alerts, filtered_alerts, fetched_alerts = run_connector_cycle(siemplify, params, context)
        if not is_test_run:
            update_connector_timestamp(
                siemplify,
                filtered_alerts=filtered_alerts,
                processed_alerts=context["processed_alerts"],
                fetched_alerts=fetched_alerts,
            )
            write_ids(siemplify, context["existing_ids"])

    except Exception:
        siemplify.LOGGER.exception("Got exception on main handler.")
        if is_test_run:
            raise

    siemplify.LOGGER.info(f"Created total of {len(alerts)} cases")
    siemplify.LOGGER.info("------------------- Main - Finished -------------------")
    siemplify.return_package(alerts)


if __name__ == "__main__":
    # Connectors are run in iterations. The interval is configurable from
    # the ConnectorsScreen UI.

    is_test: bool = not (len(sys.argv) < MIN_REQUIRED_ARGS or sys.argv[1] == "True")
    main(is_test_run=is_test)
