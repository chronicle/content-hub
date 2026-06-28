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
import re
import sys

import arrow

from soar_sdk.SiemplifyConnectors import SiemplifyConnectorExecution
from soar_sdk.SiemplifyConnectorsDataModel import AlertInfo
from soar_sdk.SiemplifyUtils import output_handler, unix_now

from EnvironmentCommon import GetEnvironmentCommonFactory
from TIPCommon.extraction import extract_connector_param
from TIPCommon.smp_io import read_ids_by_timestamp, write_ids_with_timestamp
from TIPCommon.smp_time import get_last_success_time, save_timestamp
from TIPCommon.transformation import dict_to_flat
from TIPCommon.utils import is_overflowed

from splunk.core.SplunkManager import SplunkManager
from splunk.core.UtilsManager import UNIX_FORMAT, is_approaching_timeout


# CONSTANTS
CONNECTOR_NAME = "Splunk Pull Connector"
DEFAULT_TIME_FRAME = "1h"
TIME_UNIT_MAPPER = {
    "w": "weeks",
    "d": "days",
    "h": "hours",
    "m": "minutes",
    "s": "seconds",
}
DEFAULT_ALERTS_COUNT_LIMIT = 100

connector_starting_time = unix_now()


@output_handler
def main(is_test_run):
    processed_alerts = []
    fetched_alerts = []
    siemplify = SiemplifyConnectorExecution()  # Siemplify main SDK wrapper
    siemplify.script_name = CONNECTOR_NAME

    if is_test_run:
        siemplify.LOGGER.info(
            '***** This is an "IDE Play Button"\\"Run Connector once" test run ******'
        )

    siemplify.LOGGER.info("------------------- Main - Param Init -------------------")

    server_address = extract_connector_param(
        siemplify, param_name="Server Address", is_mandatory=True
    )
    port = extract_connector_param(
        siemplify, param_name="Port", input_type=int, is_mandatory=True
    )
    username = extract_connector_param(siemplify, param_name="Username")
    password = extract_connector_param(siemplify, param_name="Password")
    api_token = extract_connector_param(siemplify, param_name="API Token")
    verify_ssl = extract_connector_param(
        siemplify, param_name="Verify SSL", default_value=False, input_type=bool
    )
    ca_certificate = extract_connector_param(
        siemplify, param_name="CA Certificate File", print_value=False
    )

    environment_field_name = extract_connector_param(
        siemplify, param_name="Environment Field Name", default_value=""
    )
    environment_regex_pattern = extract_connector_param(
        siemplify, param_name="Environment Regex Pattern", default_value=""
    )

    alerts_count_limit = extract_connector_param(
        siemplify,
        param_name="Alerts Count Limit",
        default_value=DEFAULT_ALERTS_COUNT_LIMIT,
        input_type=int,
    )
    time_frame = extract_connector_param(
        siemplify, param_name="Time Frame", default_value=DEFAULT_TIME_FRAME
    )
    python_process_timeout = extract_connector_param(
        siemplify,
        param_name="PythonProcessTimeout",
        input_type=int,
        is_mandatory=True,
        print_value=True,
    )

    siemplify.LOGGER.info("------------------- Main - Started -------------------")
    # Read already existing alerts ids
    siemplify.LOGGER.info("Reading already existing alerts ids...")
    existing_ids = read_ids_by_timestamp(siemplify)

    siemplify.LOGGER.info(f"Loaded {len(existing_ids)} existing ids")
    siemplify.LOGGER.info("Fetching alerts from splunk...")
    splunk_manager = SplunkManager(
        server_address=f"https://{server_address}:{port}",
        username=username,
        password=password,
        api_token=api_token,
        ca_certificate=ca_certificate,
        verify_ssl=verify_ssl,
        siemplify_logger=siemplify.LOGGER,
    )

    filtered_alerts = splunk_manager.get_siemplify_alerts(
        existing_ids=existing_ids,
        limit=alerts_count_limit,
        start_time=get_last_success_time(
            siemplify,
            offset_with_metric=extract_unit_and_value_from_time_frame(
                logger=siemplify.LOGGER, time_frame=time_frame
            ),
            time_format=UNIX_FORMAT,
        ),
    )
    siemplify.LOGGER.info(
        "After applying limit and filters "
        f"{len(filtered_alerts)} alerts ready to be processed"
    )

    if is_test_run:
        siemplify.LOGGER.info("This is a TEST run. Only 1 alert will be processed.")
        filtered_alerts = filtered_alerts[:1]

    environment_common = GetEnvironmentCommonFactory.create_environment_manager(
        siemplify, environment_field_name, environment_regex_pattern
    )

    for alert in filtered_alerts:
        try:
            siemplify.LOGGER.info(
                f"\nStarted processing Alert {alert.alert_id} "
                f"with timestamp {alert.timestamp}",
                alert_id=alert.alert_id,
            )

            if is_approaching_timeout(python_process_timeout, connector_starting_time):
                siemplify.LOGGER.info(
                    "Timeout is approaching. Connector will gracefully exit"
                )
                break

            alert_info = create_alert_info(environment_common, alert)

            # Update existing alerts
            existing_ids.update({alert.alert_id: arrow.utcnow().int_timestamp})
            fetched_alerts.append(alert)

            if is_overflowed(siemplify, alert_info, is_test_run):
                siemplify.LOGGER.info(
                    f"{str(alert_info.rule_generator)}-"
                    f"{str(alert_info.ticket_id)}-"
                    f"{str(alert_info.environment)}-"
                    f"{str(alert_info.device_product)} "
                    "found as overflow alert. Skipping."
                )
                # If is overflowed we should skip
                continue

            processed_alerts.append(alert_info)
            siemplify.LOGGER.info(f"Alert {alert.alert_id} was created.")

        except Exception as e:
            siemplify.LOGGER.error(
                f"Failed to process alert {alert.alert_id}", alert_id=alert.alert_id
            )
            siemplify.LOGGER.exception(e)

            if is_test_run:
                raise

        siemplify.LOGGER.info(
            f"Finished processing Alert {alert.alert_id}\n", alert_id=alert.alert_id
        )

    if not is_test_run:
        save_timestamp(siemplify, alerts=fetched_alerts)
        write_ids_with_timestamp(siemplify, existing_ids)
        siemplify.LOGGER.info(f"Write ids. Total ids = {len(existing_ids)}")

    siemplify.LOGGER.info(f"Created total of {len(processed_alerts)} cases")
    siemplify.LOGGER.info("------------------- Main - Finished -------------------")
    siemplify.return_package(processed_alerts)


def create_alert_info(environment_common, alert):
    alert_info = AlertInfo()
    alert_info.ticket_id = alert.case.ticket_id
    alert_info.display_id = alert.case.display_id
    alert_info.name = alert.case.name
    alert_info.device_vendor = alert.case.device_vendor
    alert_info.device_product = alert.case.device_product
    alert_info.start_time = alert.case.start_time
    alert_info.end_time = alert.case.end_time
    alert_info.priority = alert.case.priority
    alert_info.events = [event.as_alert_info() for event in alert.case.events]
    alert_info.rule_generator = alert.case.rule_generator
    alert_info.description = alert.case.description
    alert_info.environment = environment_common.get_environment(
        dict_to_flat(alert.case.raw_data.get("Events")[0])
    )

    return alert_info


def extract_unit_and_value_from_time_frame(logger, time_frame):
    try:
        value, unit = re.findall(r"(\d*)(\w)", time_frame)[0]
        value = int(value)
        return {TIME_UNIT_MAPPER[unit]: int(value)}
    except Exception as e:
        logger.warn(
            f'Unable to extract provided time frame "{time_frame}". '
            f'Using default time frame instead "{DEFAULT_TIME_FRAME}"'
        )
        value, unit = re.findall(r"(\d*)(\w)", DEFAULT_TIME_FRAME)[0]
        return {TIME_UNIT_MAPPER[unit]: int(value)}


if __name__ == "__main__":
    # Connectors are run in iterations. The interval is configurable from the ConnectorsScreen UI.
    is_test = not (len(sys.argv) < 2 or sys.argv[1] == "True")
    main(is_test)
