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

from EnvironmentCommon import GetEnvironmentCommonFactory
from ..core.FireEyeHelixConstants import (
    ALERTS_CONNECTOR_NAME,
    DEFAULT_TIME_FRAME,
    ACCEPTABLE_TIME_INTERVAL_IN_MINUTES,
    ALERTS_LIMIT,
    DEFAULT_SEVERITY,
    MAP_FILE,
)
from ..core.FireEyeHelixManager import FireEyeHelixManager
from soar_sdk.SiemplifyConnectors import SiemplifyConnectorExecution
from soar_sdk.SiemplifyUtils import (
    output_handler,
    utc_now,
    convert_datetime_to_unix_time,
    unix_now,
)
from TIPCommon import (
    extract_connector_param,
    read_ids,
    write_ids,
    is_overflowed,
    siemplify_save_timestamp,
    pass_whitelist_filter,
    is_approaching_timeout,
    get_last_success_time,
)
from ..core.UtilsManager import naive_time_converted_to_aware

connector_starting_time = unix_now()


@output_handler
def main(is_test_run):
    processed_alerts = []
    siemplify = SiemplifyConnectorExecution()
    siemplify.script_name = ALERTS_CONNECTOR_NAME

    if is_test_run:
        siemplify.LOGGER.info(
            '***** This is an "IDE Play Button"\\"Run Connector once" test run ******'
        )

    siemplify.LOGGER.info("------------------- Main - Param Init -------------------")

    api_root = extract_connector_param(
        siemplify, param_name="API Root", is_mandatory=True
    )
    api_token = extract_connector_param(
        siemplify, param_name="API Token", is_mandatory=True
    )
    verify_ssl = extract_connector_param(
        siemplify,
        param_name="Verify SSL",
        default_value=False,
        input_type=bool,
        is_mandatory=True,
    )
    environment_field_name = extract_connector_param(
        siemplify, param_name="Environment Field Name", default_value=""
    )
    environment_regex_pattern = extract_connector_param(
        siemplify, param_name="Environment Regex Pattern", default_value=".*"
    )

    fetch_limit = extract_connector_param(
        siemplify,
        param_name="Max Alerts To Fetch",
        input_type=int,
        default_value=ALERTS_LIMIT,
    )
    hours_backwards = extract_connector_param(
        siemplify,
        param_name="Fetch Max Hours Backwards",
        input_type=int,
        default_value=DEFAULT_TIME_FRAME,
    )

    lowest_severity = extract_connector_param(
        siemplify,
        param_name="Lowest Risk To Fetch",
        default_value=DEFAULT_SEVERITY,
        is_mandatory=True,
    )

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
    server_timezone = extract_connector_param(
        siemplify, param_name="Server Timezone", default_value="0"
    )

    try:
        siemplify.LOGGER.info("------------------- Main - Started -------------------")

        # Read already existing alerts ids
        siemplify.LOGGER.info("Reading already existing alerts ids...")
        existing_ids = read_ids(siemplify)

        siemplify.LOGGER.info("Fetching alerts...")
        manager = FireEyeHelixManager(
            api_root=api_root,
            api_token=api_token,
            verify_ssl=verify_ssl,
            siemplify=siemplify,
        )

        fetched_alerts = []
        start_time = get_last_success_time(
            siemplify, offset_with_metric={"hours": hours_backwards}
        )
        filtered_alerts = manager.get_alerts(
            existing_ids=existing_ids,
            start_time=start_time,
            lowest_severity=lowest_severity,
            timezone_offset=server_timezone,
            fetch_limit=fetch_limit,
        )

        siemplify.LOGGER.info(f"Fetched {len(filtered_alerts)} alerts")

        if is_test_run:
            siemplify.LOGGER.info("This is a TEST run. Only 1 alert will be processed.")
            filtered_alerts = filtered_alerts[:1]

        for alert in filtered_alerts:
            try:
                if len(processed_alerts) >= fetch_limit:
                    # Provide slicing for the alarms amount.
                    siemplify.LOGGER.info(
                        "Reached max number of alerts cycle. No more alerts will be processed in this cycle."
                    )
                    break

                siemplify.LOGGER.info(
                    f"Started processing Alert {alert.id} - {alert.message}",
                    alert_id=alert.id,
                )

                if is_approaching_timeout(
                    connector_starting_time, python_process_timeout
                ):
                    siemplify.LOGGER.info(
                        "Timeout is approaching. Connector will gracefully exit"
                    )
                    break

                if not pass_time_filter(siemplify, alert, server_timezone):
                    siemplify.LOGGER.info(
                        f"Alerts which are older then {ACCEPTABLE_TIME_INTERVAL_IN_MINUTES} minutes fetched. Stopping connector...."
                    )
                    break

                # Update existing alerts
                existing_ids.append(alert.id)
                fetched_alerts.append(alert)

                is_pass_whitelist_filter = pass_whitelist_filter(
                    siemplify=siemplify,
                    model=alert,
                    model_key="message",
                    whitelist_as_a_blacklist=whitelist_as_a_blacklist,
                )
                if not is_pass_whitelist_filter:
                    siemplify.LOGGER.info(
                        f"Alert {alert.id} did not pass filters skipping...."
                    )
                    continue

                siemplify.LOGGER.info("Fetching alert events...")
                alert_events = manager.get_events_for_alerts(
                    alert_id=alert.id, timezone_offset=server_timezone
                )
                siemplify.LOGGER.info(f"Fetched {len(alert_events)} alert events")

                environment_common = (
                    GetEnvironmentCommonFactory.create_environment_manager(
                        siemplify,
                        environment_field_name=environment_field_name,
                        environment_regex_pattern=environment_regex_pattern,
                        map_file=MAP_FILE,
                    )
                )
                alert_info = alert.to_alert_info(
                    environment_common, alert_events=alert_events
                )

                if is_overflowed(siemplify, alert_info, is_test_run):
                    siemplify.LOGGER.info(
                        f"{alert_info.rule_generator}-{alert_info.ticket_id}-{alert_info.environment}-{alert_info.device_product} found as overflow alert. Skipping."
                    )
                    # If is overflowed we should skip
                    continue

                processed_alerts.append(alert_info)
                siemplify.LOGGER.info(f"Alert {alert.id} was created.")

            except Exception as e:
                siemplify.LOGGER.error(
                    f"Failed to process alert {alert.id}", alert_id=alert.id
                )
                siemplify.LOGGER.exception(e)

                if is_test_run:
                    raise

            siemplify.LOGGER.info(
                f"Finished processing Alert {alert.id}", alert_id=alert.id
            )

        if not is_test_run:
            if fetched_alerts:
                new_timestamp = naive_time_converted_to_aware(
                    fetched_alerts[-1].created_at, server_timezone
                )
                siemplify_save_timestamp(siemplify, new_timestamp=new_timestamp)
                siemplify.LOGGER.info(
                    f"New timestamp {new_timestamp.isoformat()} has been saved"
                )

            write_ids(siemplify, existing_ids)

    except Exception as err:
        siemplify.LOGGER.error(f"Got exception on main handler. Error: {err}")
        siemplify.LOGGER.exception(err)
        if is_test_run:
            raise

    siemplify.LOGGER.info(f"Created total of {len(processed_alerts)} cases")
    siemplify.LOGGER.info("------------------- Main - Finished -------------------")
    siemplify.return_package(processed_alerts)


def pass_time_filter(siemplify, alert, server_timezone):
    # time filter
    end_time = convert_datetime_to_unix_time(utc_now())
    start_time = convert_datetime_to_unix_time(
        naive_time_converted_to_aware(alert.created_at, server_timezone)
    )
    time_passed_from_first_detected_in_minutes = (end_time - start_time) / 60000
    if (
        time_passed_from_first_detected_in_minutes
        <= ACCEPTABLE_TIME_INTERVAL_IN_MINUTES
    ):
        siemplify.LOGGER.info(
            f"Alert did not pass time filter. Detected approximately {time_passed_from_first_detected_in_minutes} minutes ago."
        )
        return False
    return True


if __name__ == "__main__":
    # Connectors are run in iterations. The interval is configurable from the ConnectorsScreen UI.
    is_test = not (len(sys.argv) < 2 or sys.argv[1] == "True")
    main(is_test)
