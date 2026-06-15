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
from datetime import timedelta

from soar_sdk.SiemplifyConnectors import SiemplifyConnectorExecution
from soar_sdk.SiemplifyUtils import (
    output_handler,
    utc_now,
    convert_datetime_to_unix_time,
    unix_now,
    convert_unixtime_to_datetime,
)

from TIPCommon import (
    extract_connector_param,
    dict_to_flat,
    read_ids,
    write_ids,
    is_overflowed,
    is_approaching_timeout,
    validate_timestamp,
    convert_list_to_comma_string,
    convert_comma_separated_to_list,
)
from EnvironmentCommon import GetEnvironmentCommonFactory

from ..core.StellarCyberStarlightManager import StellarCyberStarlightManager
from ..core.StellarCyberStarlightConstants import (
    SECURITY_EVENTS_CONNECTOR_NAME,
    DEFAULT_TIME_FRAME,
    ACCEPTABLE_TIME_INTERVAL_IN_MINUTES,
    WHITELIST_FILTER,
    BLACKLIST_FILTER,
    ALERTS_LIMIT,
    DEFAULT_SEVERITY,
    DB_ID_STORAGE_LIMIT,
    INVALID_VALUE_MESSAGE,
    ALERTS_FETCH_SIZE,
    TIMESTAMP_FIELD_DEFAULT_VALUE,
    TIMESTAMP_FIELD_VALUES,
)
from ..core.StellarCyberStarlightExceptions import StellarCyberStarlightInvalidValueException

connector_starting_time = unix_now()


@output_handler
def main(is_test_run):
    processed_alerts = []
    siemplify = SiemplifyConnectorExecution()  # Siemplify main SDK wrapper
    siemplify.script_name = SECURITY_EVENTS_CONNECTOR_NAME

    if is_test_run:
        siemplify.LOGGER.info(
            '***** This is an "IDE Play Button"\\"Run Connector once" test run ******'
        )

    siemplify.LOGGER.info("------------------- Main - Param Init -------------------")

    api_root = extract_connector_param(
        siemplify, param_name="API Root", is_mandatory=True
    )
    username = extract_connector_param(
        siemplify, param_name="Username", is_mandatory=True
    )
    api_key = extract_connector_param(
        siemplify,
        param_name="API Key",
        is_mandatory=False,
        print_value=False,
        remove_whitespaces=False,
    )

    api_token = extract_connector_param(
        siemplify,
        param_name="API Token",
        is_mandatory=False,
        print_value=False,
        remove_whitespaces=False,
    )

    verify_ssl = extract_connector_param(
        siemplify,
        param_name="Verify SSL",
        default_value=True,
        input_type=bool,
        is_mandatory=True,
    )
    environment_field_name = extract_connector_param(
        siemplify, param_name="Environment Field Name", default_value=""
    )
    environment_regex_pattern = extract_connector_param(
        siemplify, param_name="Environment Regex Pattern", default_value=".*"
    )
    lowest_severity_to_fetch = extract_connector_param(
        siemplify,
        param_name="Lowest Severity To Fetch",
        input_type=int,
        default_value=DEFAULT_SEVERITY,
    )
    padding_period = extract_connector_param(
        siemplify, param_name="Padding Period", input_type=int, print_value=True
    )
    hours_backwards = extract_connector_param(
        siemplify,
        param_name="Fetch Max Hours Backwards",
        input_type=int,
        default_value=DEFAULT_TIME_FRAME,
    )

    limit = extract_connector_param(
        siemplify,
        param_name="Max Events To Fetch",
        input_type=int,
        default_value=ALERTS_LIMIT,
    )

    timestamp_field = extract_connector_param(
        siemplify,
        param_name="Timestamp Field",
        is_mandatory=True,
        default_value=TIMESTAMP_FIELD_DEFAULT_VALUE,
    )

    whitelist_as_a_blacklist = extract_connector_param(
        siemplify,
        param_name="Use whitelist as a blacklist",
        is_mandatory=True,
        input_type=bool,
        print_value=True,
    )

    whitelist_filter_type = (
        BLACKLIST_FILTER if whitelist_as_a_blacklist else WHITELIST_FILTER
    )

    whitelist = siemplify.whitelist

    python_process_timeout = extract_connector_param(
        siemplify,
        param_name="PythonProcessTimeout",
        input_type=int,
        is_mandatory=True,
        print_value=True,
    )

    device_product_field = extract_connector_param(
        siemplify, "DeviceProductField", is_mandatory=True
    )

    event_class_id = extract_connector_param(
        siemplify, "EventClassId", is_mandatory=True
    )

    product_field_fallback = convert_comma_separated_to_list(
        extract_connector_param(siemplify, param_name="Product Field Fallback")
    )

    event_field_fallback = convert_comma_separated_to_list(
        extract_connector_param(siemplify, param_name="Event Field Fallback")
    )

    try:
        siemplify.LOGGER.info("------------------- Main - Started -------------------")

        if limit <= 0:
            limit = ALERTS_FETCH_SIZE
            siemplify.LOGGER.info(
                INVALID_VALUE_MESSAGE.format(ALERTS_LIMIT=ALERTS_FETCH_SIZE)
            )

        if timestamp_field not in TIMESTAMP_FIELD_VALUES:
            raise StellarCyberStarlightInvalidValueException(
                f"Invalid value provided for the parameter 'Timestamp "
                f"Field'. Please check the spelling. Supported values: "
                f"{convert_list_to_comma_string(TIMESTAMP_FIELD_VALUES)}."
            )

        # Read already existing alerts ids
        siemplify.LOGGER.info("Reading already existing alerts ids...")
        existing_ids = read_ids(siemplify)

        siemplify.LOGGER.info("Fetching alerts...")
        manager = StellarCyberStarlightManager(
            api_root=api_root,
            username=username,
            api_key=api_key,
            api_token=api_token,
            verify_ssl=verify_ssl,
            siemplify=siemplify,
        )

        if is_test_run:
            siemplify.LOGGER.info("This is a test run. Ignoring stored timestamps")
            last_success_time_datetime = validate_timestamp(
                utc_now() - timedelta(hours=hours_backwards), hours_backwards
            )
        else:
            last_success_time_datetime = validate_timestamp(
                siemplify.fetch_timestamp(datetime_format=True), hours_backwards
            )

        if padding_period and last_success_time_datetime > utc_now() - timedelta(
            hours=padding_period
        ):
            last_success_time_datetime = utc_now() - timedelta(hours=padding_period)
            siemplify.LOGGER.info(
                f"Alerts fetching using padding_period {padding_period}"
            )

        fetched_alerts = []
        filtered_alerts = manager.get_alerts(
            existing_ids=existing_ids,
            start_time=convert_datetime_to_unix_time(last_success_time_datetime),
            lowest_severity=lowest_severity_to_fetch,
            fetch_limit=limit,
            timestamp_field=timestamp_field,
        )

        siemplify.LOGGER.info(f"Fetched {len(filtered_alerts)} alerts")

        if is_test_run:
            siemplify.LOGGER.info("This is a TEST run. Only 1 alert will be processed.")
            filtered_alerts = filtered_alerts[:1]

        for alert in filtered_alerts:
            try:
                siemplify.LOGGER.info(
                    f"Started processing Alert {alert.id} - {alert.name}",
                    alert_id=alert.id,
                )

                if is_approaching_timeout(
                    connector_starting_time, python_process_timeout
                ):
                    siemplify.LOGGER.info(
                        "Timeout is approaching. Connector will gracefully exit"
                    )
                    break

                if not pass_time_filter(siemplify, alert):
                    siemplify.LOGGER.info(
                        f"Alerts which are older then "
                        f"{ACCEPTABLE_TIME_INTERVAL_IN_MINUTES} minutes "
                        f"fetched. Stopping connector...."
                    )
                    break

                # Update existing alerts
                existing_ids.append(alert.id)
                fetched_alerts.append(alert)

                if not pass_whitelist_filter(
                    siemplify, alert, whitelist, whitelist_filter_type
                ):
                    siemplify.LOGGER.info(
                        f"Alert {alert.id} did not pass filters skipping...."
                    )
                    continue

                common_env = GetEnvironmentCommonFactory.create_environment_manager(
                    siemplify=siemplify,
                    environment_field_name=environment_field_name,
                    environment_regex_pattern=environment_regex_pattern,
                )
                alert_info = alert.to_alert_info(
                    common_env,
                    device_product_field=device_product_field,
                    event_class_id=event_class_id,
                    product_field_fallback=product_field_fallback,
                    event_field_fallback=event_field_fallback,
                )
                alert_info.environment = common_env.get_environment(
                    dict_to_flat(alert.raw_data)
                )

                if is_overflowed(siemplify, alert_info, is_test_run):
                    siemplify.LOGGER.info(
                        f"{alert_info.rule_generator}-{alert_info.ticket_id}-"
                        f"{alert_info.environment}-{alert_info.device_product}"
                        f" found as overflow alert. Skipping."
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
                new_timestamp = fetched_alerts[-1].timestamp
                siemplify.save_timestamp(new_timestamp=new_timestamp)
                siemplify.LOGGER.info(
                    f"New timestamp {convert_unixtime_to_datetime(new_timestamp).isoformat()} has been saved"
                )

            write_ids(siemplify, existing_ids, stored_ids_limit=DB_ID_STORAGE_LIMIT)

    except Exception as err:
        siemplify.LOGGER.error(f"Got exception on main handler. Error: {err}")
        siemplify.LOGGER.exception(err)
        if is_test_run:
            raise

    siemplify.LOGGER.info(f"Created total of {len(processed_alerts)} cases")
    siemplify.LOGGER.info("------------------- Main - Finished -------------------")
    siemplify.return_package(processed_alerts)


def pass_time_filter(siemplify, alert):
    # time filter
    time_passed_from_first_detected_in_minutes = (unix_now() - alert.timestamp) / 60000
    if (
        time_passed_from_first_detected_in_minutes
        <= ACCEPTABLE_TIME_INTERVAL_IN_MINUTES
    ):
        siemplify.LOGGER.info(
            f"Alert did not pass time filter. Detected approximately "
            f"{time_passed_from_first_detected_in_minutes} minutes ago."
        )
        return False
    return True


def pass_whitelist_filter(siemplify, alert, whitelist, whitelist_filter_type):
    # whitelist filter
    if whitelist:
        if whitelist_filter_type == BLACKLIST_FILTER and alert.name in whitelist:
            siemplify.LOGGER.info(
                f"Alert with name: {alert.name} did not pass blacklist filter."
            )
            return False

        if whitelist_filter_type == WHITELIST_FILTER and alert.name not in whitelist:
            siemplify.LOGGER.info(
                f"Alert with name: {alert.name} did not pass whitelist filter."
            )
            return False

    return True


if __name__ == "__main__":
    # Connectors are run in iterations.
    # The interval is configurable from the ConnectorsScreen UI.
    is_test = not (len(sys.argv) < 2 or sys.argv[1] == "True")
    main(is_test)
