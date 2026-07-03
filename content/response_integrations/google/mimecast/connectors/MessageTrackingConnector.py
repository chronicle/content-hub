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
from EnvironmentCommon import GetEnvironmentCommonFactory
from soar_sdk.SiemplifyConnectors import SiemplifyConnectorExecution
from soar_sdk.SiemplifyUtils import output_handler

from TIPCommon.consts import DATETIME_FORMAT
from TIPCommon.extraction import extract_connector_param
from TIPCommon.filters import pass_whitelist_filter
from TIPCommon.smp_io import read_ids, write_ids
from TIPCommon.smp_time import (
    unix_now,
    get_last_success_time,
    is_approaching_timeout,
    save_timestamp,
)
from TIPCommon.transformation import  (
    convert_comma_separated_to_list,
    convert_list_to_comma_string,
    string_to_multi_value,
)
from TIPCommon.utils import is_overflowed

from ..core.constants import (
    CONNECTOR_NAME,
    DEFAULT_TIME_FRAME,
    DEFAULT_MAX_LIMIT,
    POSSIBLE_STATUSES,
    POSSIBLE_ROUTES,
)
from ..core.UtilsManager import (
    create_siemplify_case_wall_attachment_object,
    pass_severity_filter
)
from ..core.MimecastManager import EmailSearchCriteria, MimecastManager
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
    app_id = extract_connector_param(
        siemplify, param_name="Application ID", print_value=True
    )
    app_key = extract_connector_param(
        siemplify, param_name="Application Key",
    )
    access_key = extract_connector_param(
        siemplify, param_name="Access Key",
    )
    secret_key = extract_connector_param(
        siemplify, param_name="Secret Key",
    )
    client_id = extract_connector_param(
        siemplify, param_name="Client ID", print_value=True
    )
    client_secret = extract_connector_param(
        siemplify, param_name="Client Secret"
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
    domains = extract_connector_param(
        siemplify, param_name="Domains", is_mandatory=True, print_value=True
    )
    lowest_risk_to_fetch = extract_connector_param(
        siemplify, param_name="Lowest Risk To Fetch", print_value=True
    )
    status_filter = extract_connector_param(
        siemplify, param_name="Status Filter", print_value=True
    )
    route_filter = extract_connector_param(
        siemplify, param_name="Route Filter", print_value=True
    )
    queue_reason_filter = extract_connector_param(
        siemplify,
        param_name="Queue Reason Filter",
        print_value=True,
    )
    ingest_without_risk = extract_connector_param(
        siemplify,
        param_name="Ingest Messages Without Risk",
        is_mandatory=True,
        input_type=bool,
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
        param_name="Max Messages To Return",
        input_type=int,
        default_value=DEFAULT_MAX_LIMIT,
        print_value=True,
    )
    whitelist_as_a_blacklist = extract_connector_param(
        siemplify,
        "Use whitelist as a blacklist",
        is_mandatory=True,
        input_type=bool,
        print_value=True,
    )

    statuses = [
        status.lower() for status in convert_comma_separated_to_list(status_filter)
    ]
    routes = [route.lower() for route in convert_comma_separated_to_list(route_filter)]
    queue_reason_filter: list[str] = [
        reason.lower()
        for reason in string_to_multi_value(queue_reason_filter, only_unique=True)
    ]

    try:
        siemplify.LOGGER.info("------------------- Main - Started -------------------")

        if fetch_limit < 0:
            siemplify.LOGGER.info(
                f"Max Messages To Return must be non-negative. The default value {DEFAULT_MAX_LIMIT} "
                f"will be used"
            )
            fetch_limit = DEFAULT_MAX_LIMIT

        if hours_backwards < 0:
            siemplify.LOGGER.info(
                f"Max Hours Backwards must be non-negative. The default value {DEFAULT_TIME_FRAME} "
                f"will be used"
            )
            hours_backwards = DEFAULT_TIME_FRAME

        invalid_statuses = [
            status for status in statuses if status not in POSSIBLE_STATUSES
        ]
        invalid_routes = [route for route in routes if route not in POSSIBLE_ROUTES]

        if statuses and len(invalid_statuses) == len(statuses):
            raise Exception(
                f'Invalid values provided for "Status Filter" parameter. Possible values are: '
                f"{convert_list_to_comma_string(POSSIBLE_STATUSES)}."
            )
        elif invalid_statuses:
            statuses = [status for status in statuses if status not in invalid_statuses]
            siemplify.LOGGER.info(
                f'Following values are invalid for "Status Filter" parameter: '
                f"{convert_list_to_comma_string(invalid_statuses)}."
            )

        if routes and len(invalid_routes) == len(routes):
            raise Exception(
                f'Invalid values provided for "Route Filter" parameter. Possible values are: '
                f"{convert_list_to_comma_string(POSSIBLE_ROUTES)}."
            )
        elif invalid_routes:
            routes = [route for route in routes if route not in invalid_routes]
            siemplify.LOGGER.info(
                f'Following values are invalid for "Route Filter" parameter: '
                f"{convert_list_to_comma_string(invalid_routes)}."
            )

        # Read already existing alerts ids
        existing_ids = read_ids(siemplify)
        siemplify.LOGGER.info(f"Successfully loaded {len(existing_ids)} existing ids")

        manager = MimecastManager(
            api_root=api_root,
            app_id=app_id,
            app_key=app_key,
            access_key=access_key,
            secret_key=secret_key,
            client_id=client_id,
            client_secret=client_secret,
            verify_ssl=verify_ssl,
            siemplify=siemplify,
        )

        last_success_time = get_last_success_time(
            siemplify=siemplify,
            offset_with_metric={"hours": hours_backwards},
            time_format=DATETIME_FORMAT,
        )

        fetched_alerts = []
        filtered_alerts = manager.search_emails(
            criteria=EmailSearchCriteria(
                start_timestamp=last_success_time,
                domains=convert_comma_separated_to_list(domains),
                statuses=statuses,
                routes=routes,
                queue_reason_filter=queue_reason_filter,
            ),
            existing_ids=existing_ids,
            limit=fetch_limit,
        )

        siemplify.LOGGER.info(f"Fetched {len(filtered_alerts)} alerts")

        if is_test_run:
            siemplify.LOGGER.info("This is a TEST run. Only 1 alert will be processed.")
            filtered_alerts = filtered_alerts[:1]

        for alert in filtered_alerts:
            try:
                if is_approaching_timeout(
                    connector_starting_time=connector_starting_time,
                    python_process_timeout=script_timeout,
                ):
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

                siemplify.LOGGER.info(f"Started processing alert {alert.message_id}")

                # Update existing alerts
                existing_ids.append(alert.message_id)
                fetched_alerts.append(alert)

                if not pass_filters(
                    siemplify,
                    whitelist_as_a_blacklist,
                    alert,
                    "info",
                    lowest_risk_to_fetch,
                    ingest_without_risk,
                ):
                    continue

                environment_common = (
                    GetEnvironmentCommonFactory.create_environment_manager(
                        siemplify=siemplify,
                        environment_field_name=environment_field_name,
                        environment_regex_pattern=environment_regex_pattern,
                    )
                )
                hold_message = None
                if alert.status == "held":
                    hold_message = manager.get_hold_message_details(
                        alert.subject,
                        alert.sender,
                        alert.to,
                        alert.received,
                        alert.message_details.sent,
                    )

                alert_info = alert.get_alert_info(
                    AlertInfo(), environment_common, device_product_field, hold_message
                )
                if hold_message is not None:
                    for attachment in hold_message.attachments:
                        alert_info.attachments.append(
                            create_siemplify_case_wall_attachment_object(
                                full_file_name=attachment.filename,
                                file_contents=attachment.file_content
                            )
                        )

                if is_overflowed(siemplify, alert_info, is_test_run):
                    siemplify.LOGGER.info(
                        f"{alert_info.rule_generator}-{alert_info.ticket_id}-{alert_info.environment}"
                        f"-{alert_info.device_product} found as overflow alert. Skipping..."
                    )
                    # If is overflowed we should skip
                    continue

                processed_alerts.append(alert_info)
                siemplify.LOGGER.info(f"Alert {alert.message_id} was created.")

            except Exception as e:
                siemplify.LOGGER.error(f"Failed to process alert {alert.message_id}")
                siemplify.LOGGER.exception(e)

                if is_test_run:
                    raise

            siemplify.LOGGER.info(f"Finished processing alert {alert.message_id}")

        if not is_test_run:
            siemplify.LOGGER.info("Saving existing ids.")
            write_ids(siemplify, existing_ids)
            save_timestamp(
                siemplify=siemplify,
                alerts=fetched_alerts,
                timestamp_key="received",
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
    siemplify,
    whitelist_as_a_blacklist,
    alert,
    model_key,
    lowest_risk_to_fetch,
    ingest_without_risk,
):
    # All alert filters should be checked here
    if not pass_whitelist_filter(siemplify, whitelist_as_a_blacklist, alert, model_key):
        return False

    if not pass_severity_filter(
        siemplify, alert, lowest_risk_to_fetch, ingest_without_risk
    ):
        return False

    return True


if __name__ == "__main__":
    # Connectors are run in iterations. The interval is configurable from the ConnectorsScreen UI.
    is_test = not (len(sys.argv) < 2 or sys.argv[1] == "True")
    main(is_test)
