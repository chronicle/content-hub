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
import os
from datetime import timedelta

from soar_sdk.SiemplifyConnectors import SiemplifyConnectorExecution
from soar_sdk.SiemplifyUtils import (
    output_handler,
    utc_now,
    convert_string_to_datetime,
    convert_datetime_to_unix_time,
    unix_now,
)
from EnvironmentCommon import EnvironmentHandleForFileSystem, validate_map_file_exists
from TIPCommon import extract_connector_param

from ..core.ObserveITManager import ObserveITManager
from ..core.ObserveITValidator import ObserveITValidator
from ..core.ObserveITCommon import ObserveITCommon
from ..core.ObserveITConstants import (
    IDS_FILE,
    MAP_FILE,
    ALERTS_CONNECTOR_NAME,
    WHITELIST_FILTER,
    BLACKLIST_FILTER,
    ACCEPTABLE_TIME_INTERVAL_IN_MINUTES,
)


@output_handler
def main(is_test_run):
    connector_starting_time = unix_now()
    alerts = []
    all_alerts = []
    siemplify = SiemplifyConnectorExecution()
    siemplify.script_name = ALERTS_CONNECTOR_NAME

    if is_test_run:
        siemplify.LOGGER.info(
            '***** This is an "IDE Play Button" "Run Connector once" test run ******'
        )

    siemplify.LOGGER.info("=" * 20 + " Main - Params Init " + "=" * 20)

    environment = extract_connector_param(
        siemplify,
        param_name="Environment Field Name",
        input_type=str,
        is_mandatory=False,
        print_value=True,
    )

    environment_regex = extract_connector_param(
        siemplify,
        param_name="Environment Regex Pattern",
        input_type=str,
        is_mandatory=False,
        print_value=True,
    )

    api_root = extract_connector_param(
        siemplify,
        param_name="API Root",
        input_type=str,
        is_mandatory=True,
        print_value=True,
    )

    client_id = extract_connector_param(
        siemplify,
        param_name="Client ID",
        input_type=str,
        is_mandatory=True,
        print_value=False,
    )

    client_secret = extract_connector_param(
        siemplify,
        param_name="Client Secret",
        input_type=str,
        is_mandatory=True,
        print_value=False,
    )

    severity = extract_connector_param(
        siemplify,
        param_name="Lowest Severity To Fetch",
        input_type=str,
        is_mandatory=True,
        print_value=True,
    )

    offset_hours = extract_connector_param(
        siemplify,
        param_name="Fetch Max Hours Backwards",
        input_type=int,
        is_mandatory=False,
        print_value=True,
    )

    limit = extract_connector_param(
        siemplify,
        param_name="Max Alerts To Fetch",
        input_type=int,
        is_mandatory=False,
        print_value=True,
    )

    whitelist_as_blacklist = extract_connector_param(
        siemplify,
        param_name="Use whitelist as a blacklist",
        input_type=bool,
        is_mandatory=True,
        print_value=True,
    )

    verify_ssl = extract_connector_param(
        siemplify,
        param_name="Use SSL",
        input_type=bool,
        is_mandatory=True,
        print_value=True,
    )

    python_process_timeout = extract_connector_param(
        siemplify,
        param_name="PythonProcessTimeout",
        input_type=int,
        is_mandatory=True,
        print_value=True,
    )

    try:
        ObserveITValidator.validate_severity(severity)

        whitelist_as_blacklist = (
            BLACKLIST_FILTER if whitelist_as_blacklist else WHITELIST_FILTER
        )

        siemplify.LOGGER.info("=" * 20 + " Main - Started " + "=" * 20)

        map_file_path = os.path.join(siemplify.run_folder, MAP_FILE)
        validate_map_file_exists(map_file_path, siemplify.LOGGER)

        observe_it_common = ObserveITCommon(siemplify.LOGGER)
        environment_common = EnvironmentHandleForFileSystem(
            map_file_path,
            siemplify.LOGGER,
            environment,
            environment_regex,
            siemplify.context.connector_info.environment,
        )

        if is_test_run:
            siemplify.LOGGER.info("This is a test run. Ignoring stored timestamps")
            last_success_time_datetime = observe_it_common.validate_timestamp(
                utc_now() - timedelta(hours=offset_hours), offset_hours
            )
        else:
            last_success_time_datetime = observe_it_common.validate_timestamp(
                siemplify.fetch_timestamp(datetime_format=True), offset_hours
            )

        # Read already existing alerts ids
        existing_ids_file_path = os.path.join(siemplify.run_folder, IDS_FILE)
        existing_ids = observe_it_common.read_ids(existing_ids_file_path)

        observe_it_manager = ObserveITManager(
            api_root=api_root,
            client_id=client_id,
            client_secret=client_secret,
            verify_ssl=verify_ssl,
        )

        if is_test_run:
            siemplify.LOGGER.info("This is a TEST run. Only 1 alert will be processed.")
            limit = 1

        fetched_alerts = observe_it_manager.get_alerts(
            severity=severity,
            timestamp=convert_datetime_to_unix_time(last_success_time_datetime),
            limit=limit,
        )

        siemplify.LOGGER.info(
            f"Fetched {len(fetched_alerts)} incidents since {last_success_time_datetime.isoformat()}."
        )

        filtered_alerts = observe_it_common.filter_old_ids(
            alerts=fetched_alerts, existing_ids=existing_ids
        )

        siemplify.LOGGER.info(
            f"Filtered {len(filtered_alerts)} new incidents since {last_success_time_datetime.isoformat()}."
        )

        filtered_alerts = sorted(filtered_alerts, key=lambda inc: inc.rising_value)
    except Exception as e:
        siemplify.LOGGER.error(str(e))
        siemplify.LOGGER.exception(e)
        sys.exit(1)

    for alert in filtered_alerts:
        try:
            if observe_it_common.is_approaching_timeout(
                connector_starting_time, python_process_timeout
            ):
                siemplify.LOGGER.info(
                    "Timeout is approaching. Connector will gracefully exit."
                )
                break

            if len(alerts) >= limit:
                siemplify.LOGGER.info(f"Stop processing alerts, limit {limit} reached")
                break

            siemplify.LOGGER.info(f"Processing alert {alert.id}")

            if not alert.pass_time_filter():
                siemplify.LOGGER.info(
                    f"Alert {alert.id} is newer than {ACCEPTABLE_TIME_INTERVAL_IN_MINUTES} minutes. Stopping connector..."
                )
                # Breaking connector loop because next alerts can't pass acceptable time anyway.
                break

            all_alerts.append(alert)
            existing_ids.append(alert.id)

            if not alert.pass_whitelist_or_blacklist_filter(
                siemplify.whitelist, whitelist_as_blacklist
            ):
                siemplify.LOGGER.info(
                    f"Alert with id: {alert.id} and name: {alert.rule_name} did not pass {whitelist_as_blacklist} filter. Skipping..."
                )
                continue

            is_overflowed = False
            siemplify.LOGGER.info(
                f"Started creating alert {alert.id}", alert_id=alert.id
            )
            alert_info = alert.to_alert_info(environment_common)
            siemplify.LOGGER.info(
                f"Finished creating Alert {alert.id}", alert_id=alert.id
            )

            try:
                is_overflowed = siemplify.is_overflowed_alert(
                    environment=alert_info.environment,
                    alert_identifier=alert_info.ticket_id,
                    alert_name=alert_info.rule_generator,
                    product=alert_info.device_product,
                )

            except Exception as e:
                siemplify.LOGGER.error(
                    f"Error validation connector overflow, ERROR: {e}"
                )
                siemplify.LOGGER.exception(e)

                if is_test_run:
                    raise

            if is_overflowed:
                siemplify.LOGGER.info(
                    f"{alert_info.rule_generator}-{alert_info.ticket_id}-{alert_info.environment}-{alert_info.device_product} found as overflow alert. Skipping..."
                )
                continue
            else:
                alerts.append(alert_info)
                siemplify.LOGGER.info(f"Alert {alert.id} was created.")

        except Exception as e:
            siemplify.LOGGER.error(
                f"Failed to process incident {alert.id}", alert_id=alert.id
            )
            siemplify.LOGGER.exception(e)

            if is_test_run:
                raise

    if not is_test_run:
        if all_alerts:
            new_timestamp = convert_string_to_datetime(all_alerts[-1].rising_value)
            siemplify.save_timestamp(new_timestamp=new_timestamp)
            siemplify.LOGGER.info(
                f"New timestamp {new_timestamp.isoformat()} has been saved"
            )

        observe_it_common.write_ids(existing_ids_file_path, existing_ids)

    siemplify.LOGGER.info(f"Alerts Processed: {len(alerts)} of {len(all_alerts)}")
    siemplify.LOGGER.info(f"Created total of {len(alerts)} alerts")

    siemplify.LOGGER.info("=" * 20 + " Main - Finished " + "=" * 20)
    siemplify.return_package(alerts)


if __name__ == "__main__":
    is_test_run = not (len(sys.argv) < 2 or sys.argv[1] == "True")
    main(is_test_run)
