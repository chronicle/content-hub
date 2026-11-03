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

from datetime import timedelta
import sys

from EnvironmentCommon import GetEnvironmentCommonFactory

from soar_sdk.SiemplifyConnectors import SiemplifyConnectorExecution
from soar_sdk.SiemplifyConnectorsDataModel import AlertInfo
from soar_sdk.SiemplifyUtils import (
    output_handler,
    utc_now,
    unix_now,
    convert_datetime_to_unix_time,
)

from TIPCommon.consts import DATETIME_FORMAT
from TIPCommon.extraction import extract_connector_param
from TIPCommon.filters import pass_whitelist_filter
from TIPCommon.smp_time import (
    get_last_success_time,
    is_approaching_timeout,
    save_timestamp,
)
from TIPCommon.transformation import convert_comma_separated_to_list
from TIPCommon.utils import is_overflowed

from microsoft365_defender.core.constants import (
    ALERT_NAME_FILTER,
    API_ROOT,
    CONNECTOR_NAME,
    DEFAULT_FETCH_INTERVAL,
    DEFAULT_INCIDENT_STATUS_FILTER,
    DEFAULT_LIMIT,
    DEFAULT_MAX_LIMIT,
    DEFAULT_TIME_FRAME,
    GRAPH_API_ROOT_DEFAULT,
    INCIDENT_NAME_FILTER,
    LIMIT_OF_INCIDENTS_TO_STORE,
    LOGIN_API_ROOT_DEFAULT,
    PADDING_PERIOD_IN_MINUTES,
    POSSIBLE_STATUSES,
    TOO_MANY_REQUEST_TIMEOUT,
)
from microsoft365_defender.core.Microsoft365DefenderManager import Microsoft365DefenderManager
from microsoft365_defender.core.UtilsManager import (
    pass_severity_filter,
    validate_end_time,
    read_existing_incidents,
    write_existing_incidents,
    read_last_too_many_requests_occurrence,
    write_last_too_many_requests_occurrence,
)


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

    login_api_root = extract_connector_param(
        siemplify,
        param_name="Login API Root",
        is_mandatory=True,
        default_value=LOGIN_API_ROOT_DEFAULT,
        print_value=True
    )
    graph_api_root = extract_connector_param(
        siemplify,
        param_name="Graph API Root",
        is_mandatory=True,
        default_value=GRAPH_API_ROOT_DEFAULT,
        print_value=True
    )
    api_root = extract_connector_param(
        siemplify,
        param_name="API Root",
        is_mandatory=True,
        default_value=API_ROOT,
        print_value=True
    )
    tenant_id = extract_connector_param(
        siemplify, param_name="Tenant ID", is_mandatory=True, print_value=True
    )
    client_id = extract_connector_param(
        siemplify, param_name="Client ID", is_mandatory=True, print_value=True
    )
    client_secret = extract_connector_param(
        siemplify, param_name="Client Secret", is_mandatory=True
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
    dynamic_list_field = extract_connector_param(
        siemplify,
        param_name="Dynamic List Field",
        input_type=str,
        default_value=INCIDENT_NAME_FILTER,
        is_mandatory=False,
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
        param_name="Max Incidents To Fetch",
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
    incident_statuses = convert_comma_separated_to_list(
        extract_connector_param(
            siemplify,
            param_name="Incident Status Filter",
            default_value=DEFAULT_INCIDENT_STATUS_FILTER,
            print_value=True,
        )
    )
    alert_detection_sources = convert_comma_separated_to_list(
        extract_connector_param(
            siemplify, param_name="Alert Detection Source Filter", print_value=True
        )
    )
    alert_service_sources = convert_comma_separated_to_list(
        extract_connector_param(
            siemplify, param_name="Alert Service Source Filter", print_value=True
        )
    )
    incident_assignees = convert_comma_separated_to_list(
        extract_connector_param(
            siemplify,
            param_name="Incident Assignee Filter",
            print_value=True
        )
    )
    incident_tags = convert_comma_separated_to_list(
        extract_connector_param(
            siemplify,
            param_name="Incident Tags Filter",
            print_value=True
        )
    )
    lowest_alert_severity_to_fetch = extract_connector_param(
        siemplify, param_name="Lowest Alert Severity To Fetch", print_value=True
    )
    disable_alert_tracking = extract_connector_param(
        siemplify,
        param_name="Disable Alert Tracking",
        input_type=bool,
        print_value=True
    )

    try:
        siemplify.LOGGER.info("------------------- Main - Started -------------------")

        if hours_backwards <= 0:
            raise ValueError("Max Hours Backwards should be a positive number.")

        if fetch_limit <= 0:
            raise ValueError("Max Incidents To Fetch should be a positive number.")
        elif fetch_limit > DEFAULT_MAX_LIMIT:
            siemplify.LOGGER.info(
                f"Max Incidents To Fetch exceeded the maximum limit of {DEFAULT_MAX_LIMIT}. "
                f"The default value {DEFAULT_MAX_LIMIT} will be used"
            )
            fetch_limit = DEFAULT_MAX_LIMIT

        not_valid_statuses = set(incident_statuses).difference(POSSIBLE_STATUSES)
        if not_valid_statuses:
            raise Exception(
                f"Provided statuses - {','.join(not_valid_statuses)} are invalid, please provide list of valid values"
                f"from list - {','.join(POSSIBLE_STATUSES)}"
            )

        if dynamic_list_field.lower() not in [INCIDENT_NAME_FILTER, ALERT_NAME_FILTER]:
            raise Exception(
                f'Invalid value for "Dynamic List Field" parameter '
                f"is provided. Possible values: Incident Name, Alert Name."
            )

        incident_statuses = [
            status[0].lower() + status[1:].replace(" ", "")
            for status in incident_statuses
        ]

        last_too_many_requests_occurrence = read_last_too_many_requests_occurrence(
            siemplify
        )
        too_may_request_timeout = (
            last_too_many_requests_occurrence is not None
            and last_too_many_requests_occurrence + TOO_MANY_REQUEST_TIMEOUT
            > connector_starting_time
        )

        if too_may_request_timeout:
            raise Exception(
                f"{TOO_MANY_REQUEST_TIMEOUT / 1000} seconds didn't pass from the last TooManyRequests error"
                f"occurrence. Connector will skip this iteration."
            )

        # Read already existing alerts ids
        existing_incidents = read_existing_incidents(siemplify)
        siemplify.LOGGER.info(
            f"Successfully loaded {len(existing_incidents)} existing Incident ids"
        )

        manager = Microsoft365DefenderManager(
            api_root=api_root,
            tenant_id=tenant_id,
            client_id=client_id,
            client_secret=client_secret,
            verify_ssl=verify_ssl,
            microsoft_graph_url=graph_api_root,
            siemplify=siemplify,
            login_api_root=login_api_root,
        )

        last_success_time = get_last_success_time(
            siemplify=siemplify,
            offset_with_metric={"hours": hours_backwards},
            time_format=DATETIME_FORMAT,
        )
        start_time = last_success_time - timedelta(minutes=PADDING_PERIOD_IN_MINUTES)
        end_time = validate_end_time(
            end_time=(last_success_time + timedelta(hours=DEFAULT_FETCH_INTERVAL)),
            time_format=DATETIME_FORMAT,
        )

        fetched_incidents = []
        filtered_incidents = manager.get_incidents(
            existing_incidents=existing_incidents,
            limit=fetch_limit,
            start_time=start_time,
            end_time=end_time,
            statuses=incident_statuses,
            detection_source=alert_detection_sources,
            service_source=alert_service_sources,
            assignees=incident_assignees,
            tags=incident_tags,
            connector_starting_time=connector_starting_time,
            python_process_timeout=script_timeout,
            is_tracking_enabled=not disable_alert_tracking,
        )

        siemplify.LOGGER.info(f"Fetched {len(filtered_incidents)} incidents")

        if is_test_run:
            siemplify.LOGGER.info(
                "This is a TEST run. Only 1 incident will be processed."
            )
            filtered_incidents = filtered_incidents[:1]

        for incident in filtered_incidents:
            try:
                if is_approaching_timeout(
                    connector_starting_time=connector_starting_time,
                    python_process_timeout=script_timeout,
                ):
                    siemplify.LOGGER.info(
                        "Timeout is approaching. Connector will gracefully exit"
                    )
                    break

                siemplify.LOGGER.info(
                    f"Started processing incident {incident.incident_id} - {incident.incident_name}"
                )

                fetched_incidents.append(incident)

                if not pass_severity_filter(
                    siemplify,
                    incident,
                    lowest_severity_to_fetch,
                    "Incident",
                    "Lowest Severity To Fetch"
                ):
                    continue

                if dynamic_list_field.lower() == INCIDENT_NAME_FILTER:
                    if not pass_whitelist_filter(
                        siemplify, whitelist_as_a_blacklist, incident, "incident_name"
                    ):
                        continue

                processed_cases = []

                environment_common = (
                    GetEnvironmentCommonFactory.create_environment_manager(
                        siemplify=siemplify,
                        environment_field_name=environment_field_name,
                        environment_regex_pattern=environment_regex_pattern,
                    )
                )

                if not incident.alerts:
                    processed_cases.append(
                        incident.get_alert_info(AlertInfo(), environment_common)
                    )

                else:
                    for incident_alert in incident.alerts:
                        if not pass_severity_filter(
                            siemplify,
                            incident_alert,
                            lowest_alert_severity_to_fetch,
                            "Alert",
                            "Lowest Alert Severity To Fetch"
                        ):
                            continue

                        if dynamic_list_field.lower() == ALERT_NAME_FILTER:
                            if not pass_whitelist_filter(
                                siemplify,
                                whitelist_as_a_blacklist,
                                incident_alert,
                                "title",
                            ):
                                continue
                        processed_cases.append(
                            incident_alert.get_alert_info(
                                AlertInfo(),
                                environment_common,
                                incident.as_event(),
                                is_tracking_enabled=not disable_alert_tracking
                            )
                        )

                for alert_info in processed_cases:
                    if not disable_overflow:
                        if is_overflowed(
                            siemplify=siemplify,
                            alert_info=alert_info,
                            is_test_run=is_test_run,
                        ):
                            siemplify.LOGGER.info(
                                f"{alert_info.rule_generator}-{alert_info.ticket_id}-{alert_info.environment}"
                                f"-{alert_info.device_product} found as overflow alert. Skipping..."
                            )
                            # If is overflowed we should skip
                            continue

                    processed_alerts.append(alert_info)
                    siemplify.LOGGER.info(
                        f"Alert {alert_info.display_id} was created. Incident ID: {incident.incident_id}"
                    )

            except Exception as e:
                siemplify.LOGGER.error(
                    f"Failed to process incident {incident.incident_id}"
                )
                siemplify.LOGGER.exception(e)

                if is_test_run:
                    raise

            siemplify.LOGGER.info(
                f"Finished processing incident {incident.incident_id}"
            )

        if not is_test_run:
            siemplify.LOGGER.info("Saving all connector's state data.")

            write_last_too_many_requests_occurrence(
                siemplify, manager.too_many_request_last_occurrence
            )

            if not fetched_incidents:
                if manager.too_many_request_last_occurrence is None:
                    last_timestamp = convert_datetime_to_unix_time(
                        min(
                            utc_now(),
                            last_success_time + timedelta(hours=DEFAULT_FETCH_INTERVAL),
                        )
                    )
                    siemplify.LOGGER.info(f"Last timestamp is: {last_timestamp}")
                    siemplify.save_timestamp(new_timestamp=last_timestamp)
                else:
                    siemplify.LOGGER.info(
                        "TooManyRequests error occurred during fetch. "
                        "Timestamp will not be advanced."
                    )
            elif len(fetched_incidents) == 1:
                write_existing_incidents(
                    siemplify,
                    existing_incidents,
                    fetched_incidents,
                    LIMIT_OF_INCIDENTS_TO_STORE,
                    is_tracking_enabled=not disable_alert_tracking
                )
                save_timestamp(
                    siemplify=siemplify,
                    alerts=fetched_incidents,
                    incrementation_value=1,
                    timestamp_key="last_update_time",
                    convert_a_string_timestamp_to_unix=True,
                )
            else:
                write_existing_incidents(
                    siemplify,
                    existing_incidents,
                    fetched_incidents,
                    LIMIT_OF_INCIDENTS_TO_STORE,
                    is_tracking_enabled=not disable_alert_tracking
                )
                save_timestamp(
                    siemplify=siemplify,
                    alerts=fetched_incidents,
                    timestamp_key="last_update_time",
                    convert_a_string_timestamp_to_unix=True,
                )

    except Exception as e:
        siemplify.LOGGER.error(f"Got exception on main handler. Error: {e}")
        siemplify.LOGGER.exception(e)

        if is_test_run:
            raise

    siemplify.LOGGER.info(f"Created total of {len(processed_alerts)} cases")
    siemplify.LOGGER.info("------------------- Main - Finished -------------------")
    siemplify.return_package(processed_alerts)


def pass_filters(
    siemplify, whitelist_as_a_blacklist, alert, model_key, lowest_severity_to_fetch
):
    # All alert filters should be checked here
    if not pass_whitelist_filter(
        siemplify=siemplify,
        whitelist_as_a_blacklist=whitelist_as_a_blacklist,
        model=alert,
        model_key=model_key,
    ):
        return False

    if not pass_severity_filter(
        siemplify,
        alert,
        lowest_severity_to_fetch,
        "Incident",
        "Lowest Severity To Fetch"
    ):
        return False

    return True


if __name__ == "__main__":
    # Connectors are run in iterations. The interval is configurable from the ConnectorsScreen UI.
    is_test = not (len(sys.argv) < 2 or sys.argv[1] == "True")
    main(is_test)
