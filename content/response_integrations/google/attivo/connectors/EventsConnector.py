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
from soar_sdk.SiemplifyUtils import output_handler, unix_now
from soar_sdk.SiemplifyConnectors import SiemplifyConnectorExecution
from TIPCommon import extract_connector_param
from ..core.constants import (
    CONNECTOR_NAME,
    DEFAULT_TIME_FRAME,
    DEFAULT_LIMIT,
    DEFAULT_MAX_LIMIT,
    POSSIBLE_STATUSES,
    SEVERITY_START_MAP,
    SEVERITIES,
    DEFAULT_FETCH_INTERVAL,
)
from ..core.UtilsManager import (
    read_ids,
    write_ids,
    get_last_success_time,
    is_approaching_timeout,
    get_environment_common,
    is_overflowed,
    save_timestamp,
    pass_whitelist_filter,
    UNIX_FORMAT,
    convert_list_to_comma_string,
    validate_end_time,
)
from ..core.AttivoManager import AttivoManager
from soar_sdk.SiemplifyConnectorsDataModel import AlertInfo
import sys


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
    username = extract_connector_param(
        siemplify, param_name="Username", is_mandatory=True, print_value=True
    )
    password = extract_connector_param(
        siemplify, param_name="Password", is_mandatory=True
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
    lowest_severity_to_fetch = extract_connector_param(
        siemplify, param_name="Lowest Severity To Fetch", print_value=True
    )
    status_filter = extract_connector_param(
        siemplify, param_name="Status Filter", print_value=True, is_mandatory=True
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

    # Remove trailing and leading whitespaces from filter values
    lowest_severity_to_fetch = (
        lowest_severity_to_fetch.strip() if lowest_severity_to_fetch else ""
    )
    status_filter = status_filter.strip()

    try:
        siemplify.LOGGER.info("------------------- Main - Started -------------------")

        if fetch_limit < 0:
            siemplify.LOGGER.info(
                f"Max Events To Fetch must be non-negative. The default value {DEFAULT_LIMIT} "
                f"will be used"
            )
            fetch_limit = DEFAULT_LIMIT
        elif fetch_limit > DEFAULT_MAX_LIMIT:
            siemplify.LOGGER.info(
                f"Max Events To Fetch exceeded the maximum limit of {DEFAULT_MAX_LIMIT}. "
                f"The default value {DEFAULT_LIMIT} will be used"
            )
            fetch_limit = DEFAULT_LIMIT

        if hours_backwards < 0:
            siemplify.LOGGER.info(
                f"Max Hours Backwards must be non-negative. The default value {DEFAULT_TIME_FRAME} "
                f"will be used"
            )
            hours_backwards = DEFAULT_TIME_FRAME

        if status_filter.lower() not in POSSIBLE_STATUSES:
            raise Exception(
                f'Invalid value provided for "Status Filter" parameter. Possible values are: '
                f"{convert_list_to_comma_string(POSSIBLE_STATUSES)}."
            )

        if (
            lowest_severity_to_fetch
            and lowest_severity_to_fetch.lower() not in SEVERITIES
        ):
            raise Exception(
                f'Invalid value provided for "Lowest Severity To Fetch" parameter. Possible values are: '
                f"{convert_list_to_comma_string([severity.title() for severity in SEVERITIES])}."
            )

        # Read already existing alerts ids
        existing_ids = read_ids(siemplify)
        siemplify.LOGGER.info(f"Successfully loaded {len(existing_ids)} existing ids")

        manager = AttivoManager(
            api_root=api_root,
            username=username,
            password=password,
            verify_ssl=verify_ssl,
            siemplify_logger=siemplify.LOGGER,
        )

        last_success_time = get_last_success_time(
            siemplify=siemplify,
            offset_with_metric={"hours": hours_backwards},
            time_format=UNIX_FORMAT,
        )

        end_time = validate_end_time(
            end_time=(last_success_time + DEFAULT_FETCH_INTERVAL * 60 * 60 * 1000),
            time_format=UNIX_FORMAT,
        )

        fetched_alerts = []
        filtered_alerts = manager.get_alerts(
            existing_ids=existing_ids,
            limit=fetch_limit,
            start_timestamp=last_success_time,
            end_timestamp=end_time,
            status=status_filter,
            start_severity=(
                SEVERITY_START_MAP.get(lowest_severity_to_fetch.title())
                if lowest_severity_to_fetch
                else 0
            ),
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

                siemplify.LOGGER.info(f"Started processing alert {alert.id}")

                # Update existing alerts
                existing_ids.append(alert.id)
                fetched_alerts.append(alert)

                if not pass_filters(
                    siemplify, whitelist_as_a_blacklist, alert, "attack_name"
                ):
                    continue

                alert_info = alert.get_alert_info(
                    AlertInfo(),
                    get_environment_common(
                        siemplify, environment_field_name, environment_regex_pattern
                    ),
                    device_product_field,
                )

                if is_overflowed(siemplify, alert_info, is_test_run):
                    siemplify.LOGGER.info(
                        f"{alert_info.rule_generator}-{alert_info.ticket_id}-{alert_info.environment}"
                        f"-{alert_info.device_product} found as overflow alert. Skipping..."
                    )
                    # If is overflowed we should skip
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
            write_ids(siemplify, existing_ids)

            if not fetched_alerts:
                last_timestamp = min(
                    unix_now(),
                    last_success_time + DEFAULT_FETCH_INTERVAL * 60 * 60 * 1000,
                )
                siemplify.LOGGER.info(f"Last timestamp is: {last_timestamp}")
                siemplify.save_timestamp(new_timestamp=last_timestamp)
            else:
                save_timestamp(
                    siemplify=siemplify,
                    alerts=fetched_alerts,
                    timestamp_key="timestamp",
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
