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
from soar_sdk.SiemplifyUtils import (
    output_handler,
    unix_now,
    utc_now,
    convert_datetime_to_unix_time,
)
from soar_sdk.SiemplifyConnectors import SiemplifyConnectorExecution
from TIPCommon import extract_connector_param
from ..core.constants import CONNECTOR_NAME, DEFAULT_TIME_FRAME, DEFAULT_LIMIT
from ..core.UtilsManager import (
    read_ids,
    write_ids,
    get_last_success_time,
    is_approaching_timeout,
    get_environment_common,
    is_overflowed,
    save_timestamp,
    pass_whitelist_filter,
    DATETIME_FORMAT,
    read_utc_offset,
)
from ..core.Site24x7Manager import Site24x7Manager
from soar_sdk.SiemplifyConnectorsDataModel import AlertInfo
import sys
from datetime import timedelta, datetime
from dateutil.tz import tzoffset


connector_starting_time = unix_now()


@output_handler
def main(is_test_run):
    siemplify = SiemplifyConnectorExecution()
    siemplify.script_name = CONNECTOR_NAME
    processed_alerts = []

    if is_test_run:
        siemplify.LOGGER.info(
            '***** This is an "IDE Play Button"\\"Run Connector once" test run ******'
        )

    siemplify.LOGGER.info("------------------- Main - Param Init -------------------")

    api_root = extract_connector_param(
        siemplify, param_name="API Root", is_mandatory=True, print_value=True
    )
    client_id = extract_connector_param(
        siemplify, param_name="Client ID", is_mandatory=True, print_value=True
    )
    client_secret = extract_connector_param(
        siemplify, param_name="Client Secret", is_mandatory=True
    )
    refresh_token = extract_connector_param(
        siemplify, param_name="Refresh Token", is_mandatory=True
    )
    verify_ssl = extract_connector_param(
        siemplify,
        param_name="Verify SSL",
        is_mandatory=True,
        input_type=bool,
        print_value=True,
    )

    environment_field_name = extract_connector_param(
        siemplify, param_name="Environment Field Name", print_value=True
    )
    environment_regex_pattern = extract_connector_param(
        siemplify, param_name="Environment Regex Pattern", print_value=True
    )
    device_product_field = extract_connector_param(
        siemplify, param_name="DeviceProductField", is_mandatory=True
    )
    script_timeout = extract_connector_param(
        siemplify,
        param_name="PythonProcessTimeout",
        is_mandatory=True,
        input_type=int,
        print_value=True,
    )
    days_backwards = extract_connector_param(
        siemplify,
        param_name="Max Days Backwards",
        input_type=int,
        default_value=DEFAULT_TIME_FRAME,
        print_value=True,
    )
    fetch_limit = extract_connector_param(
        siemplify,
        param_name="Max Alert Logs To Fetch",
        input_type=int,
        default_value=DEFAULT_LIMIT,
        print_value=True,
    )
    whitelist_as_a_blacklist = extract_connector_param(
        siemplify,
        "Use whitelist as a blacklist",
        is_mandatory=True,
        input_type=bool,
        print_value=True,
    )
    disable_overflow = extract_connector_param(
        siemplify,
        "Disable Overflow",
        is_mandatory=True,
        input_type=bool,
        print_value=True,
    )

    try:
        siemplify.LOGGER.info("------------------- Main - Started -------------------")

        # Read already existing alerts ids
        existing_ids = read_ids(siemplify)
        siemplify.LOGGER.info(f"Successfully loaded {len(existing_ids)} existing ids")

        manager = Site24x7Manager(
            api_root=api_root,
            client_id=client_id,
            client_secret=client_secret,
            refresh_token=refresh_token,
            verify_ssl=verify_ssl,
            siemplify_logger=siemplify.LOGGER,
        )

        last_success_time = get_last_success_time(
            siemplify=siemplify,
            offset_with_metric={"days": days_backwards},
            time_format=DATETIME_FORMAT,
        )

        utc_offset = read_utc_offset(siemplify)

        monitors = manager.get_monitors()

        fetched_alerts = []
        filtered_alerts = manager.get_alert_logs(
            existing_ids=existing_ids,
            limit=fetch_limit,
            start_time=last_success_time,
            utc_offset=utc_offset,
        )

        siemplify.LOGGER.info(f"Fetched {len(filtered_alerts)} alerts")

        if is_test_run:
            siemplify.LOGGER.info("This is a TEST run. Only 1 alert will be processed.")
            filtered_alerts = filtered_alerts[:1]

        for alert in filtered_alerts:
            try:
                if is_approaching_timeout(script_timeout, connector_starting_time):
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

                siemplify.LOGGER.info(f"Started processing alert {alert.msg}")

                # Update existing alerts
                existing_ids.append(alert.id)
                fetched_alerts.append(alert)

                if not pass_filters(siemplify, whitelist_as_a_blacklist, alert, "msg"):
                    continue

                alert_info = alert.get_alert_info(
                    AlertInfo(),
                    get_environment_common(
                        siemplify, environment_field_name, environment_regex_pattern
                    ),
                    device_product_field,
                    [monitor.display_name for monitor in monitors],
                )

                if not disable_overflow:
                    if is_overflowed(siemplify, alert_info, is_test_run):
                        siemplify.LOGGER.info(
                            f"{alert_info.rule_generator}-{alert_info.ticket_id}-{alert_info.environment}"
                            f"-{alert_info.device_product} found as overflow alert. Skipping..."
                        )
                        # If is overflowed we should skip
                        continue

                processed_alerts.append(alert_info)
                siemplify.LOGGER.info(f"Alert {alert.msg} was created.")

            except Exception as e:
                siemplify.LOGGER.error(f"Failed to process alert {alert.msg}")
                siemplify.LOGGER.exception(e)

                if is_test_run:
                    raise

            siemplify.LOGGER.info(f"Finished processing alert {alert.msg}")

        if not is_test_run:
            siemplify.LOGGER.info("Saving existing ids.")
            write_ids(siemplify, existing_ids)

            if not fetched_alerts:
                incremented_datetime = datetime.combine(
                    last_success_time + timedelta(days=DEFAULT_TIME_FRAME),
                    datetime.min.time(),
                    tzoffset(None, utc_offset * 60 * 60),
                )
                last_timestamp = convert_datetime_to_unix_time(
                    min(utc_now(), incremented_datetime)
                )

                siemplify.LOGGER.info(f"Last timestamp is: {last_timestamp}")
                siemplify.save_timestamp(new_timestamp=last_timestamp)
            else:
                save_timestamp(
                    siemplify=siemplify,
                    alerts=fetched_alerts,
                    timestamp_key="sent_time",
                )

    except Exception as e:
        siemplify.LOGGER.error(f"Got exception on main handler. Error: {e}")
        siemplify.LOGGER.exception(e)

        if is_test_run:
            raise

    siemplify.LOGGER.info(f"Created total of {len(processed_alerts)} cases")
    siemplify.LOGGER.info("------------------- Main - Finished -------------------")
    siemplify.return_package(processed_alerts)


def pass_filters(siemplify, whitelist_as_a_blacklist, alert, model_key):
    # All alert filters should be checked here
    if not pass_whitelist_filter(siemplify, whitelist_as_a_blacklist, alert, model_key):
        return False

    return True


if __name__ == "__main__":
    # Connectors are run in iterations. The interval is configurable from the ConnectorsScreen UI.
    is_test = not (len(sys.argv) < 2 or sys.argv[1] == "True")
    main(is_test)
