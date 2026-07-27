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

# ============================= IMPORTS ===================================== #
from __future__ import annotations
import sys
from soar_sdk.SiemplifyUtils import convert_unixtime_to_datetime, output_handler
from soar_sdk.SiemplifyConnectors import SiemplifyConnectorExecution
from TIPCommon import (
    extract_connector_param,
    convert_datetime_to_unix_time,
    siemplify_fetch_timestamp,
    siemplify_save_timestamp,
    validate_timestamp,
    is_overflowed,
)
from ..core.ConnectorManager import ZabbixConnector
from ..core.ZabbixManager import ZabbixManager


@output_handler
def main(is_test_run=False):
    connector_scope = SiemplifyConnectorExecution()
    connector_scope.script_name = "Zabbix Connector"

    try:
        if is_test_run:
            connector_scope.LOGGER.info(
                '***** This is an "IDE Play Button" "Run Connector once" '
                "test run ******"
            )

        connector_scope.LOGGER.info(
            "==================== Main - Param Init ===================="
        )

        api_root = extract_connector_param(
            connector_scope,
            param_name="Api Root",
            input_type=str,
            is_mandatory=True,
            print_value=True,
        )

        username = extract_connector_param(
            connector_scope,
            param_name="Username",
            input_type=str,
            is_mandatory=True,
            print_value=True,
        )

        password = extract_connector_param(
            connector_scope,
            param_name="Password",
            input_type=str,
            is_mandatory=True,
            print_value=False,
        )

        max_hours_backwards = extract_connector_param(
            connector_scope,
            param_name="Fetch Max Hours Backwards",
            input_type=int,
            default_value=1,
            is_mandatory=False,
            print_value=True,
        )

        only_problematic = extract_connector_param(
            connector_scope,
            param_name="Only Problematic Triggers",
            input_type=bool,
            is_mandatory=False,
            default_value=False,
            print_value=True,
        )

        verify_ssl = extract_connector_param(
            connector_scope,
            param_name="Verify SSL",
            default_value=False,
            input_type=bool,
            is_mandatory=True,
        )

        connector_scope.LOGGER.info(
            "------------------- Main - Started -------------------"
        )

        last_success_time_datetime = validate_timestamp(
            siemplify_fetch_timestamp(connector_scope, datetime_format=True),
            max_hours_backwards,
        )
        last_success_time_ms = convert_datetime_to_unix_time(last_success_time_datetime)

        connector_scope.LOGGER.info(
            f"Last success time: {last_success_time_datetime.isoformat()}"
        )

        connector_scope.LOGGER.info("Connecting to Zabbix")
        zabbix_manager = ZabbixManager(api_root, username, password, verify_ssl)
        connector_scope.LOGGER.info("Successfully connected.")

        connector_scope.LOGGER.info("Parsing tags from whitelist.")
        tags = ZabbixConnector.parse_whitelist_tags(connector_scope.whitelist)
        connector_scope.LOGGER.info(f"Found {len(list(tags.keys()))} tags.")

        zabbix_connector = ZabbixConnector(
            connector_scope=connector_scope, zabbix_manager=zabbix_manager, tags=tags
        )

        # Get alerts
        connector_scope.LOGGER.info("Collecting triggers from Zabbix.")
        triggers = zabbix_connector.get_triggers(
            last_success_time_ms=last_success_time_ms, only_problematic=only_problematic
        )
        connector_scope.LOGGER.info(f"Found {len(triggers)} active triggers.")

        connector_scope.LOGGER.info("Collecting events for triggers.")
        events = zabbix_connector.get_events(triggers, is_test=is_test_run)
        connector_scope.LOGGER.info(f"Found {len(events)} events.")

        processed_alerts = []
        alerts = []

        for event in events:
            try:
                # Process each Zabbix event ( = Siemplify Alert)
                connector_scope.LOGGER.info(f"Processing event {event['eventid']}.")
                _is_overflowed = False
                case_info = zabbix_connector.create_alert_info(event)

                if not case_info:
                    # Event was skipped due to a host in maintenance
                    continue

                processed_alerts.append(case_info)

                _is_overflowed = is_overflowed(
                    connector_scope, alert_info=case_info, is_test_run=is_test_run
                )

                if _is_overflowed:
                    connector_scope.LOGGER.info(
                        f"{case_info.rule_generator}-{case_info.ticket_id}"
                        f"-{case_info.environment}-{case_info.device_product} "
                        "found as overflow event. Skipping..."
                    )
                    continue

                else:
                    alerts.append(case_info)
                    connector_scope.LOGGER.info(
                        'Finished processing event {event["eventid"]}'
                    )

            except KeyError as error:
                connector_scope.LOGGER.error(
                    f"Event's data is missing mandatory key: {error}"
                )

                if is_test_run:
                    raise

            except Exception as e:
                connector_scope.LOGGER.error(
                    f'Failed to process event {event.get("eventid")}'
                )
                connector_scope.LOGGER.exception(e)

                if is_test_run:
                    raise

        if not is_test_run:
            if processed_alerts:
                new_timestamp = sorted(
                    processed_alerts, key=lambda alert: alert.end_time
                )[-1].end_time
                siemplify_save_timestamp(connector_scope, new_timestamp=new_timestamp)
                connector_scope.LOGGER.info(
                    "New timestamp "
                    f"{convert_unixtime_to_datetime(new_timestamp).isoformat()}"
                    " has been saved"
                )

        connector_scope.LOGGER.info(f"Created total of {len(alerts)} cases")
        connector_scope.LOGGER.info(
            "------------------- Main - Finished -------------------"
        )
        connector_scope.return_package(alerts)

    except Exception as e:
        connector_scope.LOGGER.error(e)
        connector_scope.LOGGER.exception(e)

        if is_test_run:
            raise


if __name__ == "__main__":
    is_test_run = not (len(sys.argv) < 2 or sys.argv[1] == "True")
    main(is_test_run)
