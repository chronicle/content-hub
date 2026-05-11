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
from TIPCommon import (
    extract_connector_param,
    read_ids,
    write_ids,
    save_timestamp,
    is_overflowed,
    get_last_success_time,
)
from EnvironmentCommon import GetEnvironmentCommonFactory
from ..core.LogRhythmManager import LogRhythmRESTManager
from soar_sdk.SiemplifyConnectors import SiemplifyConnectorExecution
from soar_sdk.SiemplifyConnectorsDataModel import AlertInfo
from soar_sdk.SiemplifyUtils import output_handler, unix_now
from ..core.utils import is_approaching_timeout, pass_whitelist_filter
from ..core.constants import (
    REST_ALARMS_CONNECTOR_SCRIPT_NAME,
    DEFAULT_MAX_ALARMS_TO_FETCH,
    DEFAULT_MAX_HOURS_BACKWARDS,
    REST_ALARMS_DATE_FORMAT,
    DATETIME_FORMAT,
)

connector_starting_time = unix_now()


@output_handler
def main(is_test_run):
    siemplify = SiemplifyConnectorExecution()
    siemplify.script_name = REST_ALARMS_CONNECTOR_SCRIPT_NAME
    processed_alerts = []
    all_alarms = []
    if is_test_run:
        siemplify.LOGGER.info(
            '***** This is an "IDE Play Button"\\"Run Connector once" test run ******'
        )

    siemplify.LOGGER.info("------------------- Main - Param Init -------------------")

    api_root = extract_connector_param(
        siemplify, param_name="API Root", is_mandatory=True, print_value=True
    )
    api_token = extract_connector_param(
        siemplify, param_name="API Token", is_mandatory=True, remove_whitespaces=False
    )
    verify_ssl = extract_connector_param(
        siemplify,
        param_name="Verify SSL",
        is_mandatory=True,
        default_value=False,
        input_type=bool,
        print_value=True,
    )

    device_product_field = extract_connector_param(
        siemplify, param_name="DeviceProductField", is_mandatory=True, print_value=True
    )
    environment_field_name = extract_connector_param(
        siemplify, param_name="Environment Field Name"
    )
    environment_regex_pattern = extract_connector_param(
        siemplify, param_name="Environment Regex Pattern"
    )
    script_timeout = extract_connector_param(
        siemplify,
        param_name="PythonProcessTimeout",
        is_mandatory=True,
        input_type=int,
        print_value=True,
    )
    max_hours_backwards = extract_connector_param(
        siemplify,
        param_name="Max Hours Backwards",
        input_type=int,
        default_value=DEFAULT_MAX_HOURS_BACKWARDS,
        print_value=True,
    )
    max_alarms_to_fetch = extract_connector_param(
        siemplify,
        param_name="Max Alarms To Fetch",
        input_type=int,
        default_value=DEFAULT_MAX_ALARMS_TO_FETCH,
        print_value=True,
    )
    whitelist_as_a_blacklist = extract_connector_param(
        siemplify,
        "Use whitelist as a blacklist",
        is_mandatory=True,
        input_type=bool,
        print_value=True,
        default_value=False,
    )

    siemplify.LOGGER.info("------------------- Main - Started -------------------")

    try:
        manager = LogRhythmRESTManager(
            api_root=api_root,
            api_key=api_token,
            verify_ssl=verify_ssl,
            siemplify=siemplify,
        )

        common_environment = GetEnvironmentCommonFactory().create_environment_manager(
            siemplify, environment_field_name, environment_regex_pattern
        )
        # Read already existing alerts ids
        siemplify.LOGGER.info("Reading already existing alerts ids...")
        existing_ids = read_ids(siemplify)
        siemplify.LOGGER.info(f"Found {len(existing_ids)} existing ids in ids.json")

        last_success_time = get_last_success_time(
            siemplify=siemplify,
            offset_with_metric={"hours": max_hours_backwards},
            time_format=DATETIME_FORMAT,
        )

        siemplify.LOGGER.info("Fetching alerts..")
        filtered_alarms = manager.get_alarms(
            inserted_after=last_success_time.strftime(REST_ALARMS_DATE_FORMAT),
            existing_ids=existing_ids,
            limit=max_alarms_to_fetch,
        )
        filtered_alarms = sorted(filtered_alarms, key=lambda alarm: alarm.timestamp)
        siemplify.LOGGER.info(f"Fetched {len(filtered_alarms)} new alarms")

        if is_test_run:
            siemplify.LOGGER.info("This is a TEST run. Only 1 alarm will be processed.")
            filtered_alarms = filtered_alarms[:1]

        for alarm in filtered_alarms:
            try:
                if len(processed_alerts) >= max_alarms_to_fetch:
                    # Provide slicing for the alerts amount.
                    siemplify.LOGGER.info(
                        "Reached max number of alarms cycle. "
                        "No more alerts will be processed in this cycle."
                    )
                    break

                if is_approaching_timeout(connector_starting_time, script_timeout):
                    siemplify.LOGGER.info(
                        "Timeout is approaching. Connector will gracefully exit"
                    )
                    break

                siemplify.LOGGER.info(
                    f"Started processing alarm {alarm.alarm_id} with rule: "
                    f"{alarm.alarm_rule_name}"
                )
                all_alarms.append(alarm)

                if not pass_whitelist_filter(
                    siemplify, whitelist_as_a_blacklist, alarm, "alarm_rule_name"
                ):
                    siemplify.LOGGER.info(
                        "Alarm {alarm.alarm_id} did not pass whitelist filter. "
                        "Skipping..."
                    )
                    continue

                alarm_summary_details = None

                try:  # Get alarm's summary details
                    siemplify.LOGGER.info("Fetching additional alarm details")
                    alarm_summary_details = manager.get_alarm_summary(alarm.alarm_id)
                except Exception as error:
                    siemplify.LOGGER.error(
                        f"Failed to get alarm summary. Error is: {error}"
                    )

                events = []
                try:  # Get alarm's events
                    siemplify.LOGGER.info("Loading alarm events...")
                    events = manager.get_alarm_events(alarm.alarm_id)
                    siemplify.LOGGER.info(f"Loaded {len(events)} events")
                except Exception as error:
                    siemplify.LOGGER.error(f"Failed to load events. Error is: {error}")

                alert_info = alarm.get_alert_info(
                    alert_info=AlertInfo(),
                    device_product_field=device_product_field,
                    environment_common=common_environment,
                    alarm_summary_details=alarm_summary_details,
                    events=events,
                )

                if is_overflowed(siemplify, alert_info, is_test_run):
                    siemplify.LOGGER.info(
                        f"{str(alert_info.rule_generator)}-"
                        f"{str(alert_info.ticket_id)}-{str(alert_info.environment)}-"
                        f"{str(alert_info.device_product)} found as overflow alert. "
                        f"Skipping."
                    )
                    # If is overflowed we should skip
                    continue

                processed_alerts.append(alert_info)
                siemplify.LOGGER.info(f"Alert {alarm.alarm_id} was created")

            except Exception as e:
                siemplify.LOGGER.error(f"Failed to process alarm {alarm.alarm_id}\n")
                siemplify.LOGGER.exception(e)

                if is_test_run:
                    raise

            siemplify.LOGGER.info(f"Finished processing alarm {alarm.alarm_id}\n")

        if not is_test_run:
            if all_alarms:
                save_timestamp(siemplify=siemplify, alerts=all_alarms)
                write_ids(
                    siemplify, existing_ids + [alarm.alarm_id for alarm in all_alarms]
                )

    except Exception as error:
        siemplify.LOGGER.error(f"Got exception on main handler. Error: {error}")
        siemplify.LOGGER.exception(error)

        if is_test_run:
            raise

    siemplify.LOGGER.info(f"Created total of {len(processed_alerts)} cases")
    siemplify.LOGGER.info("------------------- Main - Finished -------------------")
    siemplify.return_package(processed_alerts)


if __name__ == "__main__":
    # Connectors are run in iterations. The interval is configurable
    # from the ConnectorsScreen UI.
    is_test = not (len(sys.argv) < 2 or sys.argv[1] == "True")
    main(is_test)
