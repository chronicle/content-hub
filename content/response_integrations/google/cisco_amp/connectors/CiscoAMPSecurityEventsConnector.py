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
import sys

from soar_sdk.SiemplifyConnectors import SiemplifyConnectorExecution
from soar_sdk.SiemplifyConnectorsDataModel import AlertInfo
from soar_sdk.SiemplifyUtils import output_handler, unix_now

from TIPCommon import (
    extract_connector_param,
    write_ids,
    read_ids,
    get_last_success_time,
    is_approaching_timeout,
    is_overflowed,
    save_timestamp,
    pass_whitelist_filter,
)
from EnvironmentCommon import GetEnvironmentCommonFactory

from ..core.CiscoAMPManager import CiscoAMPManager
from ..core.consts import (
    SECURITY_EVENTS_CONNECTOR_NAME,
    SEVERITIES,
    DEFAULT_MAX_LIMIT,
    DEFAULT_TIME_FRAME,
    SEVERITIES_MAP,
    MAX_EVENTS,
    STORED_IDS_LIMIT,
)

connector_starting_time = unix_now()


@output_handler
def main(is_test_run):
    siemplify = SiemplifyConnectorExecution()
    siemplify.script_name = SECURITY_EVENTS_CONNECTOR_NAME
    processed_alerts = []
    overflowed = 0

    if is_test_run:
        siemplify.LOGGER.info(
            '***** This is an "IDE Play Button"\\"Run Connector once" test run ******'
        )

    try:
        siemplify.LOGGER.info(
            "------------------- Main - Param Init -------------------"
        )

        api_root = extract_connector_param(
            siemplify,
            param_name="API Root",
            is_mandatory=True,
            print_value=True,
            input_type=str,
        )
        client_id = extract_connector_param(
            siemplify,
            param_name="Client ID",
            is_mandatory=True,
            print_value=True,
            input_type=str,
        )
        api_key = extract_connector_param(
            siemplify, param_name="API Key", is_mandatory=True, input_type=str
        )
        verify_ssl = extract_connector_param(
            siemplify,
            param_name="Verify SSL",
            is_mandatory=True,
            default_value=True,
            input_type=bool,
            print_value=True,
        )
        environment_field_name = extract_connector_param(
            siemplify,
            param_name="Environment Field Name",
            default_value="",
            print_value=True,
            input_type=str,
        )
        environment_regex_pattern = extract_connector_param(
            siemplify,
            param_name="Environment Regex Pattern",
            print_value=True,
            input_type=str,
        )
        script_timeout = extract_connector_param(
            siemplify,
            param_name="PythonProcessTimeout",
            is_mandatory=True,
            input_type=int,
            default_value=180,
            print_value=True,
        )
        lowest_severity_to_fetch = extract_connector_param(
            siemplify,
            param_name="Lowest Severity To Fetch",
            is_mandatory=False,
            default_value="",
            print_value=True,
            input_type=str,
        )
        fetch_events_without_severity = extract_connector_param(
            siemplify,
            param_name="Fetch Events Without Severity",
            is_mandatory=False,
            default_value=True,
            input_type=bool,
            print_value=True,
        )
        hours_backwards = extract_connector_param(
            siemplify,
            param_name="Max Hours Backwards",
            input_type=int,
            default_value=DEFAULT_TIME_FRAME,
            print_value=True,
        )
        fetch_limit = extract_connector_param(
            siemplify,
            param_name="Max Events To Fetch",
            input_type=int,
            default_value=DEFAULT_MAX_LIMIT,
            print_value=True,
        )
        whitelist_as_a_blacklist = extract_connector_param(
            siemplify,
            "Use whitelist as a blacklist",
            is_mandatory=True,
            input_type=bool,
            print_value=True,
        )

        device_product_field = extract_connector_param(
            siemplify, "DeviceProductField", is_mandatory=True, input_type=str
        )

        whitelist = siemplify.whitelist

        siemplify.LOGGER.info("------------------- Main - Started -------------------")

        if (
            lowest_severity_to_fetch
            and lowest_severity_to_fetch.strip() not in SEVERITIES
        ):
            raise Exception(
                f"Alert severity {lowest_severity_to_fetch} is invalid. Valid values are: {', '.join(SEVERITIES)}"
            )
        severities = SEVERITIES_MAP.get(lowest_severity_to_fetch)

        if fetch_limit <= 0:
            siemplify.LOGGER.info(
                "Max Events To Fetch must be positive. "
                "The default value {} will be used".format(DEFAULT_MAX_LIMIT)
            )
            fetch_limit = DEFAULT_MAX_LIMIT

        if fetch_limit > MAX_EVENTS:
            siemplify.LOGGER.info(
                "Max Events To Fetch exceeded maximum value of {}. "
                "The default value {} will be used".format(
                    MAX_EVENTS, DEFAULT_MAX_LIMIT
                )
            )
            fetch_limit = DEFAULT_MAX_LIMIT

        if hours_backwards < 0:
            siemplify.LOGGER.info(
                "Max Hours Backwards must be non-negative. "
                "The default value {} will be used".format(DEFAULT_TIME_FRAME)
            )
            hours_backwards = DEFAULT_TIME_FRAME

        # Read already existing alerts ids
        existing_ids = read_ids(siemplify)
        siemplify.LOGGER.info(f"Successfully loaded {len(existing_ids)} existing ids")

        manager = CiscoAMPManager(
            server_address=api_root,
            client_id=client_id,
            api_key=api_key,
            use_ssl=verify_ssl,
            siemplify=siemplify,
        )

        fetched_alerts = []
        filtered_alerts = manager.get_events(
            existing_ids=existing_ids,
            limit=fetch_limit,
            start_date=get_last_success_time(
                siemplify=siemplify, offset_with_metric={"hours": hours_backwards}
            ).isoformat(),
        )
        filtered_alerts = sorted(filtered_alerts, key=lambda alert: alert.timestamp_ms)
        siemplify.LOGGER.info(f"Fetched {len(filtered_alerts)} alerts")

        if is_test_run:
            siemplify.LOGGER.info("This is a TEST run. Only 1 alert will be processed.")
            filtered_alerts = filtered_alerts[:1]

        for alert in filtered_alerts:
            try:
                if is_approaching_timeout(connector_starting_time, script_timeout):
                    siemplify.LOGGER.info(
                        "Timeout is approaching. Connector will gracefully exit"
                    )
                    break

                if len(processed_alerts) >= fetch_limit:
                    # Provide slicing for the alerts amount.
                    siemplify.LOGGER.info(
                        "Reached max number of alerts cycle. No more alerts will be processed in this cycle."
                    )
                    break

                if alert.id in existing_ids:
                    siemplify.LOGGER.info(
                        f"Alert {alert.id} skipped since it has been fetched before"
                    )
                    fetched_alerts.append(alert)
                    continue

                # Update existing alerts
                fetched_alerts.append(alert)
                existing_ids.append(alert.id)

                siemplify.LOGGER.info(
                    f"Started processing alert {alert.id} - {alert.event_type}"
                )

                if not pass_filters(
                    siemplify=siemplify,
                    whitelist_as_a_blacklist=whitelist_as_a_blacklist,
                    whitelist=whitelist,
                    alert=alert,
                    model_key="event_type",
                    fetch_events_without_severity=fetch_events_without_severity,
                    severities=severities,
                ):
                    continue

                # Get environment
                common_environment = (
                    GetEnvironmentCommonFactory.create_environment_manager(
                        siemplify=siemplify,
                        environment_field_name=environment_field_name,
                        environment_regex_pattern=environment_regex_pattern,
                    )
                )
                alert_info = alert.get_alert_info(
                    AlertInfo(), common_environment, device_product_field
                )

                if is_overflowed(siemplify, alert_info, is_test_run):
                    siemplify.LOGGER.info(
                        "{alert_name}-{alert_identifier}-{environment}-{product} "
                        "found as overflow alert. Skipping.".format(
                            alert_name=alert_info.rule_generator,
                            alert_identifier=alert_info.ticket_id,
                            environment=alert_info.environment,
                            product=alert_info.device_product,
                        )
                    )
                    # If is overflowed we should skip
                    overflowed += 1
                    continue

                processed_alerts.append(alert_info)
                siemplify.LOGGER.info(f"Alert {alert.id} was created.")

            except Exception as e:
                siemplify.LOGGER.error(f"Failed to process alert {alert.id}")
                siemplify.LOGGER.exception(e)

                if is_test_run:
                    raise

            siemplify.LOGGER.info(f"Finished processing alert {alert.id}")

        if not is_test_run:
            siemplify.LOGGER.info("Saving existing ids.")
            write_ids(siemplify, existing_ids, stored_ids_limit=STORED_IDS_LIMIT)
            save_timestamp(
                siemplify=siemplify, alerts=fetched_alerts, timestamp_key="timestamp_ms"
            )

        siemplify.LOGGER.info(
            f"Alerts processed: {len(processed_alerts)} out of {len(fetched_alerts)} (Overflowed: {overflowed})"
        )

    except Exception as e:
        siemplify.LOGGER.error(f"Got exception on main handler. Error: {str(e)}")
        siemplify.LOGGER.exception(e)

        if is_test_run:
            raise

    siemplify.LOGGER.info(f"Created total of {len(processed_alerts)} cases")
    siemplify.LOGGER.info("------------------- Main - Finished -------------------")
    siemplify.return_package(processed_alerts)


def pass_filters(
    siemplify,
    whitelist_as_a_blacklist,
    whitelist,
    alert,
    model_key,
    fetch_events_without_severity,
    severities,
):
    # All alert filters should be checked here
    if not pass_whitelist_filter(
        siemplify=siemplify,
        whitelist_as_a_blacklist=whitelist_as_a_blacklist,
        model=alert,
        model_key=model_key,
        whitelist=whitelist,
    ):
        return False

    if (not fetch_events_without_severity) and alert.severity is None:
        siemplify.LOGGER.info(
            f"Alert with id: '{alert.id}' has no severity assigned. Skipping..."
        )
        return False

    if (alert.severity is not None) and severities:
        if alert.severity not in severities:
            siemplify.LOGGER.info(
                f"Alert with id: '{alert.id}' did not pass severity filter."
            )
            return False

    return True


if __name__ == "__main__":
    # Connectors are run in iterations. The interval is configurable from the ConnectorsScreen UI.
    is_test = not (len(sys.argv) < 2 or sys.argv[1] == "True")
    main(is_test)
