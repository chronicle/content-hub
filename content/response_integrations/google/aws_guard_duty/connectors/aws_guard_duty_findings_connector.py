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

"""AWS GuardDuty findings connector implementation."""

from __future__ import annotations

import sys
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from EnvironmentCommon import GetEnvironmentCommonFactory
from soar_sdk.SiemplifyConnectors import SiemplifyConnectorExecution
from soar_sdk.SiemplifyUtils import (
    convert_datetime_to_unix_time,
    output_handler,
    unix_now,
)
from TIPCommon.extraction import extract_connector_param
from TIPCommon.filters import pass_whitelist_filter
from TIPCommon.smp_io import read_ids_by_timestamp, write_ids_with_timestamp
from TIPCommon.smp_time import (
    get_last_success_time,
    is_approaching_timeout,
    save_timestamp,
)
from TIPCommon.utils import is_overflowed

from ..core.aws_guard_duty_manager import AWSGuardDutyManager
from ..core.consts import (
    CONNECTOR_NAME,
    DEFAULT_FETCH_LIMIT,
    DEFAULT_HOURS_BACKWARDS,
    PAGE_SIZE,
)
from ..core.datamodels import FindingsQuery
from ..core.utils import extract_integration_params

if TYPE_CHECKING:
    import datetime

    from ..core.datamodels import Finding

MIN_SEVERITY = 1
MAX_SEVERITY = 8


def _extract_params(siemplify: SiemplifyConnectorExecution) -> dict[str, Any]:
    """Extract all connector configuration parameters.

    Args:
        siemplify: SiemplifyConnectorExecution instance.

    Returns:
        Dict containing parameter values.

    Raises:
        ValueError: If configuration parameters are invalid.

    """
    config = extract_integration_params(siemplify, is_connector=True)

    verify_ssl = extract_connector_param(
        siemplify,
        param_name="Verify SSL",
        default_value=True,
        input_type=bool,
        print_value=True,
    )
    detector_id = extract_connector_param(siemplify, param_name="Detector ID", is_mandatory=True, print_value=True)
    environment_field_name = extract_connector_param(
        siemplify,
        param_name="Environment Field Name",
        default_value="",
        print_value=True,
    )
    environment_regex_pattern = extract_connector_param(
        siemplify,
        param_name="Environment Regex Pattern",
        default_value="",
        print_value=True,
    )
    fetch_limit = extract_connector_param(
        siemplify,
        param_name="Max Findings To Fetch",
        input_type=int,
        is_mandatory=False,
        default_value=DEFAULT_FETCH_LIMIT,
        print_value=True,
    )
    hours_backwards = extract_connector_param(
        siemplify,
        param_name="Fetch Max Hours Backwards",
        input_type=int,
        is_mandatory=False,
        default_value=DEFAULT_HOURS_BACKWARDS,
        print_value=True,
    )
    min_severity = extract_connector_param(
        siemplify,
        param_name="Lowest Severity To Fetch",
        is_mandatory=True,
        print_value=True,
        input_type=int,
    )

    if min_severity < MIN_SEVERITY or min_severity > MAX_SEVERITY:
        msg = f"Severity {min_severity} is invalid. Valid values are in range from {MIN_SEVERITY} to {MAX_SEVERITY}."
        raise ValueError(msg)

    whitelist_as_a_blacklist = extract_connector_param(
        siemplify,
        "Use whitelist as a blacklist",
        is_mandatory=True,
        input_type=bool,
        print_value=True,
    )
    python_process_timeout = extract_connector_param(
        siemplify,
        param_name="PythonProcessTimeout",
        input_type=int,
        is_mandatory=True,
        print_value=True,
    )

    params = {
        "verify_ssl": verify_ssl,
        "detector_id": detector_id,
        "environment_field_name": environment_field_name,
        "environment_regex_pattern": environment_regex_pattern,
        "fetch_limit": fetch_limit,
        "hours_backwards": hours_backwards,
        "min_severity": min_severity,
        "whitelist_as_a_blacklist": whitelist_as_a_blacklist,
        "python_process_timeout": python_process_timeout,
    }
    return config, params


@dataclass
class ConnectorContext:
    """Dataclass representing the connector execution context.

    Attributes:
        manager: AWSGuardDutyManager instance.
        params: Dict of connector parameters.
        existing_ids: Dict of already seen IDs.
        last_success_time: Datetime offset of last execution.
        siemplify: SiemplifyConnectorExecution instance.
        connector_starting_time: Unix epoch ms when execution started.

    """

    manager: AWSGuardDutyManager
    params: dict[str, Any]
    existing_ids: dict[str, Any]
    last_success_time: datetime.datetime
    siemplify: SiemplifyConnectorExecution
    connector_starting_time: int


def _fetch_all_findings(
    context: ConnectorContext,
) -> tuple[list[Finding], list[Finding]]:
    """Fetch all findings from GuardDuty, paginating and filtering.

    Args:
        context: ConnectorContext instance.

    Returns:
        Tuple of (filtered_findings, ignored_findings).

    """
    manager = context.manager
    params = context.params
    existing_ids = context.existing_ids
    last_success_time = context.last_success_time
    siemplify = context.siemplify
    connector_starting_time = context.connector_starting_time
    query = FindingsQuery(
        detector_id=params["detector_id"],
        min_severity=params["min_severity"],
        page_size=min(params["fetch_limit"], PAGE_SIZE),
        updated_at=convert_datetime_to_unix_time(last_success_time),
        asc=True,
    )
    search_after_token, fetched_findings = manager.get_findings_page(query=query)

    filtered_findings = []
    ignored_findings = []
    whitelist = siemplify.whitelist

    while fetched_findings:
        if is_approaching_timeout(
            python_process_timeout=params["python_process_timeout"],
            connector_starting_time=connector_starting_time,
        ):
            break

        new_alerts = [finding for finding in fetched_findings if finding.id not in existing_ids]

        for alert in new_alerts:
            if not pass_whitelist_filter(
                siemplify=siemplify,
                whitelist_as_a_blacklist=params["whitelist_as_a_blacklist"],
                model=alert,
                model_key="type",
                whitelist=whitelist,
            ):
                existing_ids.update({alert.id: unix_now()})
                ignored_findings.append(alert)
            else:
                filtered_findings.append(alert)

        if len(filtered_findings) >= params["fetch_limit"]:
            break

        if search_after_token:
            query = FindingsQuery(
                detector_id=params["detector_id"],
                min_severity=params["min_severity"],
                page_size=min(params["fetch_limit"], PAGE_SIZE),
                updated_at=convert_datetime_to_unix_time(last_success_time),
                search_after_token=search_after_token,
                asc=True,
            )
            search_after_token, fetched_findings = manager.get_findings_page(query=query)
        else:
            break

    return filtered_findings, ignored_findings


def _process_alert(
    context: ConnectorContext,
    alert: Finding,
    *,
    is_test_run: bool,
) -> tuple[Any, bool]:
    """Process a single AWS GuardDuty finding and format it as alert info.

    Args:
        context: ConnectorContext instance.
        alert: AWS GuardDuty finding object.
        is_test_run: True if this is a test run.

    Returns:
        Tuple of (alert_info, is_overflow).

    """
    siemplify = context.siemplify
    existing_ids = context.existing_ids
    environment_field_name = context.params["environment_field_name"]
    environment_regex_pattern = context.params["environment_regex_pattern"]

    siemplify.LOGGER.info(f"Started processing Alert {alert.id}", alert_id=alert.id)

    existing_ids.update({alert.id: unix_now()})

    common_env = GetEnvironmentCommonFactory.create_environment_manager(
        siemplify=siemplify,
        environment_field_name=environment_field_name,
        environment_regex_pattern=environment_regex_pattern,
    )
    alert_info = alert.as_alert_info(common_env)

    siemplify.LOGGER.info(
        f"Finding ID: {alert.id}, Type: {alert.type}, "
        f"CreatedTime: {alert.created_time}, "
        f"UpdatedTime: {alert.updated_time}, "
        f"Severity: {alert.severity}, Count: {alert.count}"
    )

    if is_overflowed(siemplify, alert_info, is_test_run):
        siemplify.LOGGER.info(
            f"{alert_info.rule_generator}-{alert_info.ticket_id}-"
            f"{alert_info.environment}-{alert_info.device_product} "
            "found as overflow alert. Skipping."
        )
        return alert_info, True

    siemplify.LOGGER.info(f"Alert {alert.id} was created.")
    return alert_info, False


def _run_connector(siemplify: SiemplifyConnectorExecution, *, is_test_run: bool) -> list[Any]:
    """Execute the connector logic to fetch and process findings.

    Args:
        siemplify: SiemplifyConnectorExecution instance.
        is_test_run: True if this is a test run.

    Returns:
        List of processed alerts.

    """
    connector_starting_time = unix_now()
    processed_alerts = []
    processed_findings = []

    config, params = _extract_params(siemplify)

    siemplify.LOGGER.info("Connecting to AWS GuardDuty Service")
    manager = AWSGuardDutyManager(
        config=config,
        verify_ssl=params["verify_ssl"],
        siemplify_logger=siemplify.LOGGER,
    )
    manager.test_connectivity()  # this validates the credentials
    siemplify.LOGGER.info("Successfully connected to AWS GuardDuty service")

    # Read already existing alerts ids
    siemplify.LOGGER.info("Loading existing ids from IDS file.")
    existing_ids = read_ids_by_timestamp(siemplify)
    siemplify.LOGGER.info(f"Found {len(existing_ids)} existing ids in ids.json")

    last_success_time = get_last_success_time(
        siemplify=siemplify,
        offset_with_metric={"hours": params["hours_backwards"]},
    )

    siemplify.LOGGER.info(f"Fetching findings with update time greater than {last_success_time.isoformat()}")

    context = ConnectorContext(
        manager=manager,
        params=params,
        existing_ids=existing_ids,
        last_success_time=last_success_time,
        siemplify=siemplify,
        connector_starting_time=connector_starting_time,
    )
    filtered_findings, ignored_findings = _fetch_all_findings(context=context)

    siemplify.LOGGER.info(
        f"Found new {len(filtered_findings)} findings out of total of"
        f" {len(filtered_findings) + len(ignored_findings)} findings."
    )

    if is_test_run:
        siemplify.LOGGER.info("This is a TEST run. Only 1 alert will be processed.")
        filtered_findings = filtered_findings[:1]

    # process alerts in connector cycle
    for alert in filtered_findings:
        if len(processed_alerts) >= params["fetch_limit"]:
            # Provide slicing for the alarms amount.
            siemplify.LOGGER.info(
                "Reached max number of alerts cycle of value"
                f" {params['fetch_limit']}. No more alerts will be processed in"
                " this cycle."
            )
            break

        if is_approaching_timeout(
            connector_starting_time=connector_starting_time,
            python_process_timeout=params["python_process_timeout"],
        ):
            siemplify.LOGGER.info("Timeout is approaching. Connector will gracefully exit")
            break

        try:
            alert_info, is_overflow = _process_alert(
                context=context,
                alert=alert,
                is_test_run=is_test_run,
            )
            # Add alert to processed findings (regardless of overflow status) to mark it as processed
            processed_findings.append(alert)

            if not is_overflow:
                processed_alerts.append(alert_info)

        except Exception:
            siemplify.LOGGER.exception(f"Failed to process alert {alert.id}", alert_id=alert.id)
            if is_test_run:
                raise

        siemplify.LOGGER.info(f"Finished processing Alert {alert.id}", alert_id=alert.id)

    if not is_test_run:
        siemplify.LOGGER.info("Saving existing ids.")
        write_ids_with_timestamp(siemplify, existing_ids)
        # Save timestamp based on the processed findings (processed = alert info created, regardless of overflow
        # status) and the ignored findings (= alerts that didn't pass whitelist/blacklist). New timestamp
        # should be the latest among all of those
        save_timestamp(
            siemplify=siemplify,
            alerts=processed_findings + ignored_findings,
            timestamp_key="updated_time_ms",
        )

    return processed_alerts


@output_handler
def main(*, is_test_run: bool) -> None:
    """Run AWS GuardDuty findings connector.

    Args:
        is_test_run: True if this is a test run.

    """
    siemplify = SiemplifyConnectorExecution()  # Siemplify main SDK wrapper
    siemplify.script_name = CONNECTOR_NAME

    try:
        processed_alerts = _run_connector(siemplify, is_test_run=is_test_run)
    except Exception:
        siemplify.LOGGER.exception("Got exception on main handler.")
        if is_test_run:
            raise
        processed_alerts = []

    siemplify.LOGGER.info(f"Created total of {len(processed_alerts)} cases")
    siemplify.LOGGER.info("------------------- Main - Finished -------------------")
    siemplify.return_package(processed_alerts)


if __name__ == "__main__":
    # Connectors are run in iterations. The interval is configurable from the ConnectorsScreen UI.
    min_args = 2
    is_test = not (len(sys.argv) < min_args or sys.argv[1] == "True")
    main(is_test_run=is_test)
