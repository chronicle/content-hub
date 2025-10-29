############################## TERMS OF USE ################################### # noqa: E266
# The following code is provided for demonstration purposes only, and should  #
# not be used without independent verification. Recorded Future makes no      #
# representations or warranties, express, implied, statutory, or otherwise,   #
# regarding this code, and provides it strictly "as-is".                      #
# Recorded Future shall not be liable for, and you assume all risk of         #
# using the foregoing.                                                        #
###############################################################################

# ============================================================================#
# title           :Recorded Future - Playbook Alerts Connector.py
# description     :Contains the Recorded Future Playbook Alerts Connector
# author          :support@recordedfuture.com                       noqa: ERA001
# date            :10-31-2025
# python_version  :3.11                                             noqa: ERA001
# product_version :8.0
# ============================================================================#

from __future__ import annotations

import sys
from datetime import datetime

from EnvironmentCommon import GetEnvironmentCommonFactory
from soar_sdk.SiemplifyConnectors import SiemplifyConnectorExecution
from soar_sdk.SiemplifyConnectorsDataModel import AlertInfo
from soar_sdk.SiemplifyUtils import output_handler, unix_now
from TIPCommon.consts import UNIX_FORMAT
from TIPCommon.extraction import extract_connector_param
from TIPCommon.smp_io import read_ids, write_ids
from TIPCommon.smp_time import (
    get_last_success_time,
    is_approaching_timeout,
    save_timestamp,
)
from TIPCommon.utils import is_overflowed
from TIPCommon.validation import ParameterValidator

from ..core.constants import (
    CONNECTOR_DATETIME_FORMAT,
    CSV_DELIMETER,
    DEFAULT_LIMIT,
    DEFAULT_TIME_FRAME,
    PLAYBOOK_ALERT_CATEGORIES,
    PLAYBOOK_ALERT_CONNECTOR_NAME,
    PLAYBOOK_ALERT_PRIORITIES,
    PLAYBOOK_ALERT_STATUSES,
)
from ..core.RecordedFutureManager import RecordedFutureManager

connector_starting_time = unix_now()


@output_handler
def main(is_test_run):
    processed_alerts = []
    siemplify = SiemplifyConnectorExecution()
    siemplify.script_name = PLAYBOOK_ALERT_CONNECTOR_NAME

    if is_test_run:
        siemplify.LOGGER.info(
            '***** This is an "IDE Play Button"\\"Run Connector once" test run ******',
        )

    siemplify.LOGGER.info("------------------- Main - Param Init -------------------")
    param_validator = ParameterValidator(siemplify=siemplify)

    api_url = extract_connector_param(
        siemplify,
        param_name="API URL",
        is_mandatory=True,
    )
    api_key = extract_connector_param(
        siemplify,
        param_name="API Key",
        is_mandatory=True,
    )
    verify_ssl = extract_connector_param(
        siemplify,
        param_name="Verify SSL",
        is_mandatory=True,
        input_type=bool,
    )

    environment_field_name = extract_connector_param(
        siemplify,
        param_name="Environment Field Name",
    )
    environment_regex_pattern = extract_connector_param(
        siemplify,
        param_name="Environment Regex Pattern",
    )

    playbook_alert_categories = param_validator.validate_csv(
        param_name="playbook_alert_categories",
        csv_string=extract_connector_param(
            siemplify,
            "Playbook Alert Categories",
            is_mandatory=False,
            input_type=str,
        ),
        delimiter=CSV_DELIMETER,
        possible_values=PLAYBOOK_ALERT_CATEGORIES,
        default_value=[],
    )
    playbook_alert_statuses = param_validator.validate_csv(
        param_name="playbook_alert_statuses",
        csv_string=extract_connector_param(
            siemplify,
            "Playbook Alert Statuses",
            is_mandatory=False,
            input_type=str,
        ),
        delimiter=CSV_DELIMETER,
        possible_values=PLAYBOOK_ALERT_STATUSES,
        default_value=[],
    )
    playbook_alert_priorities = param_validator.validate_csv(
        param_name="playbook_alert_priorities",
        csv_string=extract_connector_param(
            siemplify,
            "Playbook Alert Priorities",
            is_mandatory=False,
            input_type=str,
        ),
        delimiter=CSV_DELIMETER,
        possible_values=PLAYBOOK_ALERT_PRIORITIES,
        default_value=[],
    )

    script_timeout = extract_connector_param(
        siemplify,
        param_name="PythonProcessTimeout",
        is_mandatory=True,
        input_type=int,
        print_value=True,
    )
    fetch_limit = param_validator.validate_positive(
        param_name="fetch_limit",
        value=extract_connector_param(
            siemplify,
            param_name="Max Alerts To Fetch",
            input_type=int,
        ),
        default_value=DEFAULT_LIMIT,
    )
    hours_backwards = param_validator.validate_positive(
        param_name="hours_backwards",
        value=extract_connector_param(
            siemplify,
            param_name="Fetch Max Hours Backwards",
            input_type=int,
            default_value=DEFAULT_TIME_FRAME,
        ),
        default_value=DEFAULT_TIME_FRAME,
    )

    severity = extract_connector_param(
        siemplify,
        param_name="Severity",
        is_mandatory=False,
    )

    enable_overflow = extract_connector_param(
        siemplify,
        "Enable Overflow",
        is_mandatory=True,
        input_type=bool,
    )

    try:
        siemplify.LOGGER.info("------------------- Main - Started -------------------")

        # Read already existing alerts ids
        siemplify.LOGGER.info("Reading already existing alerts ids...")
        existing_ids = read_ids(siemplify)

        siemplify.LOGGER.info("Fetching playbook alerts...")
        manager = RecordedFutureManager(
            api_url,
            api_key,
            verify_ssl=verify_ssl,
            siemplify=siemplify,
        )

        start_timestamp = get_last_success_time(
            siemplify=siemplify,
            offset_with_metric={"hours": hours_backwards},
            time_format=UNIX_FORMAT,
        )
        created_from = datetime.fromtimestamp(start_timestamp / 1000).strftime(
            CONNECTOR_DATETIME_FORMAT,
        )
        created_until = datetime.now().strftime(CONNECTOR_DATETIME_FORMAT)
        fetched_alerts = []
        filtered_alerts = manager.get_playbook_alerts(
            existing_ids=existing_ids,
            limit=fetch_limit,
            category=playbook_alert_categories,
            statuses=playbook_alert_statuses,
            priority=playbook_alert_priorities,
            severity=severity,
            created_from=created_from,
            created_until=created_until,
        )

        siemplify.LOGGER.info(f"Fetched {len(filtered_alerts)} alerts")

        if is_test_run:
            siemplify.LOGGER.info("This is a TEST run. Only 1 alert will be processed.")
            filtered_alerts = filtered_alerts[:1]

        for alert in filtered_alerts:
            try:
                if len(processed_alerts) >= fetch_limit:
                    # Provide slicing for the alerts amount.
                    siemplify.LOGGER.info(
                        "Reached max number of alerts cycle."
                        "No more alerts will be processed in this cycle.",
                    )
                    break

                siemplify.LOGGER.info(
                    f"Started processing alert {alert.id} - {alert.category}",
                    alert_id=alert.id,
                )

                if is_approaching_timeout(connector_starting_time, script_timeout):
                    siemplify.LOGGER.info(
                        "Timeout is approaching. Connector will gracefully exit",
                    )
                    break

                # Update existing alerts
                existing_ids.append(alert.id)
                fetched_alerts.append(alert)

                common_env = GetEnvironmentCommonFactory.create_environment_manager(
                    siemplify=siemplify,
                    environment_field_name=environment_field_name,
                    environment_regex_pattern=environment_regex_pattern,
                )
                alert_info = alert.get_alert_info(
                    AlertInfo(),
                    environment_common=common_env,
                )

                if enable_overflow and is_overflowed(
                    siemplify,
                    alert_info,
                    is_test_run,
                ):
                    siemplify.LOGGER.info(
                        f"{alert_info.rule_generator}-{alert_info.ticket_id}-{alert_info.environment}-{alert_info.device_product}"
                        + " found as overflow alert. Skipping.",
                    )
                    # If is overflowed we should skip
                    continue

                processed_alerts.append(alert_info)
                siemplify.LOGGER.info(f"Alert {alert.id} was created.")

            except Exception as e:
                siemplify.LOGGER.error(
                    f"Failed to process alert {alert.id}",
                    alert_id=alert.id,
                )
                siemplify.LOGGER.exception(e)

                if is_test_run:
                    raise

            siemplify.LOGGER.info(
                f"Finished processing alert {alert.id}",
                alert_id=alert.id,
            )

        if not is_test_run:
            save_timestamp(
                siemplify=siemplify,
                alerts=fetched_alerts,
                timestamp_key="start",
            )
            write_ids(siemplify, existing_ids)

    except Exception as e:
        siemplify.LOGGER.error(f"Got exception on main handler. Error: {e}")
        siemplify.LOGGER.exception(e)

        if is_test_run:
            raise

    siemplify.LOGGER.info(f"Created total of {len(processed_alerts)} cases")
    siemplify.LOGGER.info("------------------- Main - Finished -------------------")
    siemplify.return_package(processed_alerts)


if __name__ == "__main__":
    # Connectors are run in iterations. The interval is configurable from the ConnectorsScreen UI.
    is_test = not (len(sys.argv) < 2 or sys.argv[1] == "True")
    main(is_test)
