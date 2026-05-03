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
from soar_sdk.SiemplifyUtils import output_handler
import sys
from soar_sdk.SiemplifyUtils import unix_now
from soar_sdk.SiemplifyConnectors import CaseInfo, SiemplifyConnectorExecution
from ..core.LogRhythmManager import LogRhythmRESTManager
from TIPCommon import extract_connector_param, read_ids, write_ids, is_overflowed
from EnvironmentCommon import GetEnvironmentCommonFactory
from ..core.utils import (
    is_approaching_timeout,
    pass_whitelist_filter,
    validate_timestamp_arrow,
    get_filtered_alerts,
    validate_positive_integer,
    fetch_timestamp,
    save_timestamp_arrow,
)
from ..core.constants import (
    CASES_CONNECTOR_NAME,
    ALERTS_LIMIT,
    DEFAULT_DAYS_BACKWARDS,
    CASE_PRIORITY_MAPPING,
    CASES_STATUS_NUMBER_DEFAULT,
    CASES_COUNT_DEFAULT,
)

connector_starting_time = unix_now()


def validate_priority_integer(number):
    if number not in CASE_PRIORITY_MAPPING.values():
        raise Exception(
            f"Lowest Priority To Fetch parameter must match one of the following: "
            f"{CASE_PRIORITY_MAPPING.values()}"
        )


@output_handler
def main(is_test_run=False):
    siemplify = SiemplifyConnectorExecution()
    siemplify.script_name = CASES_CONNECTOR_NAME
    processed_alerts = []
    all_alerts = []

    if is_test_run:
        siemplify.LOGGER.info(
            '***** This is an "IDE Play Button"\\"Run Connector once" test run ******'
        )

    siemplify.LOGGER.info("------------------- Main - Param Init -------------------")

    api_root = extract_connector_param(
        siemplify, param_name="Api Root", is_mandatory=True
    )
    api_token = extract_connector_param(
        siemplify, param_name="Api Token", remove_whitespaces=False
    )
    verify_ssl = extract_connector_param(
        siemplify, param_name="Verify SSL", input_type=bool, is_mandatory=True
    )

    product_field_name = extract_connector_param(
        siemplify, param_name="DeviceProductField", is_mandatory=True
    )
    environment_field_name = extract_connector_param(
        siemplify, param_name="Environment Field Name", default_value=""
    )
    environment_regex_pattern = extract_connector_param(
        siemplify, param_name="Environment Regex Pattern"
    )
    script_timeout = extract_connector_param(
        siemplify,
        param_name="PythonProcessTimeout",
        input_type=int,
        is_mandatory=True,
        print_value=True,
    )

    max_days_backwards = extract_connector_param(
        siemplify,
        param_name="Max Days Backwards",
        input_type=int,
        default_value=DEFAULT_DAYS_BACKWARDS,
        print_value=True,
    )
    lowest_priority = extract_connector_param(
        siemplify,
        param_name="Lowest Priority To Fetch",
        input_type=int,
        print_value=True,
    )
    alerts_count_limit = extract_connector_param(
        siemplify,
        param_name="Alerts Count Limit",
        input_type=int,
        is_mandatory=True,
        default_value=ALERTS_LIMIT,
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

    try:
        siemplify.LOGGER.info("------------------- Main - Started -------------------")
        validate_positive_integer(
            script_timeout, "Timeout parameter should be positive."
        )
        validate_positive_integer(
            max_days_backwards, "Max Days Backwards parameter should be positive."
        )
        validate_positive_integer(
            alerts_count_limit, "Alerts Count Limit parameter should be positive."
        )
        if lowest_priority:
            validate_priority_integer(lowest_priority)

        manager = LogRhythmRESTManager(
            api_root=api_root,
            api_key=api_token,
            verify_ssl=verify_ssl,
            siemplify=siemplify,
        )

        common_environment = GetEnvironmentCommonFactory.create_environment_manager(
            siemplify, environment_field_name, environment_regex_pattern
        )

        siemplify.LOGGER.info("Reading already existing alerts ids...")
        existing_ids = read_ids(siemplify)
        siemplify.LOGGER.info(f"Found {len(existing_ids)} existing ids in ids.json")

        siemplify.LOGGER.info("Fetching alerts..")
        last_success_time = validate_timestamp_arrow(
            str(fetch_timestamp(siemplify)), max_days_backwards
        )

        alerts = manager.get_cases(
            created_after=last_success_time,
            priority=lowest_priority,
            status_number=CASES_STATUS_NUMBER_DEFAULT,
            limit=max(alerts_count_limit, CASES_COUNT_DEFAULT),
        )
        filtered_alerts = get_filtered_alerts(alerts, existing_ids)
        siemplify.LOGGER.info(f"Found {len(filtered_alerts)} alerts.")

        if is_test_run:
            siemplify.LOGGER.info("This is a TEST run. Only 1 alarm will be processed.")
            filtered_alerts = alerts[-1:]

        for alert in filtered_alerts:
            try:
                if len(processed_alerts) >= alerts_count_limit:
                    # Provide slicing for the alerts amount.
                    siemplify.LOGGER.info(
                        "Reached max number of alerts cycle. "
                        "No more alerts will be processed in this cycle."
                    )
                    break

                if is_approaching_timeout(connector_starting_time, script_timeout):
                    siemplify.LOGGER.info(
                        "Timeout is approaching. Connector will gracefully exit"
                    )
                    break

                siemplify.LOGGER.info(f"Processing Alert {alert.name}, ID: {alert.id}")
                all_alerts.append(alert)

                if not pass_whitelist_filter(
                    siemplify, whitelist_as_a_blacklist, alert, "name"
                ):
                    siemplify.LOGGER.info(
                        f"Alert {alert.id} did not pass whitelist filter. Skipping..."
                    )
                    continue

                case_info = alert.create_case_info(
                    case_info=CaseInfo(),
                    product_field_name=product_field_name,
                    environment_common=common_environment,
                )

                events = manager.get_evidences(case_id=alert.number)
                if events:
                    case_info.events.extend([event.as_flat_event() for event in events])

                if is_overflowed(siemplify, case_info, is_test_run):
                    siemplify.LOGGER.info(
                        f"{str(case_info.rule_generator)}-"
                        f"{str(case_info.ticket_id)}-{str(case_info.environment)}-"
                        f"{str(case_info.device_product)} found as overflow alert. "
                        f"Skipping."
                    )
                    continue

                processed_alerts.append(case_info)
                siemplify.LOGGER.info(f"Alert {alert.id} was created")

            except Exception as e:
                siemplify.LOGGER.error(f"Failed to process case {alert.id}")
                siemplify.LOGGER.exception(e)

                if is_test_run:
                    raise

            siemplify.LOGGER.info(f"Finished processing case {alert.id}")

        if not is_test_run:
            if all_alerts:
                save_timestamp_arrow(
                    siemplify=siemplify, alerts=all_alerts, timestamp_key="date_created"
                )
                write_ids(siemplify, existing_ids + [case.id for case in all_alerts])

        # Return data
        siemplify.LOGGER.info(f"Created total of {len(processed_alerts)} cases")
        siemplify.LOGGER.info("------------------- Main - Finished -------------------")
        siemplify.return_package(processed_alerts)

    except Exception as e:
        siemplify.LOGGER.error(f"Got exception on main handler. Error: {e}")
        siemplify.LOGGER.exception(e)

        if is_test_run:
            raise


if __name__ == "__main__":
    is_test = not (len(sys.argv) < 2 or sys.argv[1] == "True")
    main(is_test)
