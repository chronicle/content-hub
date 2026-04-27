from __future__ import annotations
import sys

from EnvironmentCommon import GetEnvironmentCommonFactory
from soar_sdk.SiemplifyConnectors import SiemplifyConnectorExecution
from soar_sdk.SiemplifyConnectorsDataModel import AlertInfo
from soar_sdk.SiemplifyUtils import (
    output_handler,
    utc_now,
    convert_datetime_to_unix_time,
    unix_now,
)
from TIPCommon import (
    extract_connector_param,
    get_last_success_time,
    read_ids,
    write_ids,
    UNIX_FORMAT,
    is_overflowed,
    save_timestamp,
    is_approaching_timeout,
)
from ..core.VectraManager import VectraManager
from ..core.constants import (
    CONNECTOR_NAME,
    DEFAULT_TIME_FRAME,
    ACCEPTABLE_TIME_INTERVAL_IN_MINUTES,
    WHITELIST_FILTER,
    BLACKLIST_FILTER,
    DETECTION_CATEGORIES,
    MAX_IDS,
)

connector_starting_time = unix_now()


@output_handler
def main(is_test_run):
    processed_alerts = []
    siemplify = SiemplifyConnectorExecution()  # Siemplify main SDK wrapper
    siemplify.script_name = CONNECTOR_NAME

    if is_test_run:
        siemplify.LOGGER.info(
            '***** This is an "IDE Play Button"\\"Run Connector once" test run ******'
        )

    siemplify.LOGGER.info("------------------- Main - Param Init -------------------")

    api_root = extract_connector_param(
        siemplify, param_name="API Root", input_type=str, is_mandatory=True
    )
    api_token = extract_connector_param(
        siemplify, param_name="API Token", input_type=str, is_mandatory=True
    )
    verify_ssl = extract_connector_param(
        siemplify,
        param_name="Verify SSL",
        default_value=True,
        input_type=bool,
        is_mandatory=True,
    )
    environment_field_name = extract_connector_param(
        siemplify, param_name="Environment Field Name", default_value="", input_type=str
    )
    environment_regex_pattern = extract_connector_param(
        siemplify, param_name="Environment Regex Pattern", input_type=str
    )

    fetch_limit = extract_connector_param(
        siemplify, param_name="Max Detections To Fetch", input_type=int
    )
    hours_backwards = extract_connector_param(
        siemplify,
        param_name="Fetch Max Hours Backwards",
        input_type=int,
        default_value=DEFAULT_TIME_FRAME,
    )

    lowest_certainty = extract_connector_param(
        siemplify,
        param_name="Lowest Certainty Score To Fetch",
        input_type=int,
        default_value=0,
    )
    lowest_threat_score = extract_connector_param(
        siemplify,
        param_name="Lowest Threat Score To Fetch",
        input_type=int,
        is_mandatory=True,
    )
    category_filter = extract_connector_param(
        siemplify,
        param_name="Category Filter",
        default_value=",".join(DETECTION_CATEGORIES),
        input_type=str,
    )

    whitelist_as_a_blacklist = extract_connector_param(
        siemplify,
        "Use whitelist as a blacklist",
        input_type=bool,
        is_mandatory=True,
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

    try:
        siemplify.LOGGER.info("------------------- Main - Started -------------------")

        # Read already existing alerts ids
        siemplify.LOGGER.info("Reading already existing alerts ids...")
        existing_ids = read_ids(siemplify)

        siemplify.LOGGER.info("Fetching threats...")
        manager = VectraManager(api_root, api_token, verify_ssl, siemplify)

        fetched_alerts = []
        filtered_alerts = manager.get_detections(
            existing_ids=existing_ids,
            limit=fetch_limit,
            start_timestamp=get_last_success_time(
                siemplify=siemplify,
                offset_with_metric={"hours": hours_backwards},
                time_format=UNIX_FORMAT,
            ),
            threat_score=lowest_threat_score,
            certainty_score=lowest_certainty,
            categories=category_filter,
        )

        siemplify.LOGGER.info(f"Fetched {len(filtered_alerts)} threats")

        if is_test_run:
            siemplify.LOGGER.info("This is a TEST run. Only 1 alert will be processed.")
            filtered_alerts = filtered_alerts[:1]

        for alert in filtered_alerts:
            try:
                if len(processed_alerts) >= fetch_limit:
                    # Provide slicing for the alarms amount.
                    siemplify.LOGGER.info(
                        "Reached max number of alerts cycle."
                        " No more alerts will be processed in this cycle."
                    )
                    break

                siemplify.LOGGER.info(
                    f"Started processing Alert {alert.detection_id}"
                    f" - {alert.detection_type} ",
                    alert_id=alert.detection_id,
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
                        "Alerts which are older then"
                        f" {ACCEPTABLE_TIME_INTERVAL_IN_MINUTES} minutes fetched."
                        " Stopping connector...."
                    )
                    break

                # Update existing alerts
                existing_ids.append(alert.detection_id)
                fetched_alerts.append(alert)

                if not pass_whitelist_filter(
                    siemplify, alert, whitelist, whitelist_filter_type
                ):
                    siemplify.LOGGER.info(
                        f"Alert {alert.detection_id} did not pass filters skipping...."
                    )
                    continue

                environment_common = (
                    GetEnvironmentCommonFactory.create_environment_manager(
                        siemplify, environment_field_name, environment_regex_pattern
                    )
                )
                alert_info = alert.get_alert_info(
                    AlertInfo(), environment_common, device_product_field
                )

                if is_overflowed(siemplify, alert_info, is_test_run):
                    siemplify.LOGGER.info(
                        f"{str(alert_info.rule_generator)}-{str(alert_info.ticket_id)}"
                        f"-{str(alert_info.environment)}"
                        f"-{str(alert_info.device_product)}"
                        " found as overflow alert. Skipping."
                    )
                    # If is overflowed we should skip
                    continue

                processed_alerts.append(alert_info)
                siemplify.LOGGER.info(f"Alert {alert.detection_id} was created.")

            except Exception as e:
                siemplify.LOGGER.error(
                    f"Failed to process alert {alert.detection_id}",
                    alert_id=alert.detection_id,
                )
                siemplify.LOGGER.exception(e)

                if is_test_run:
                    raise

            siemplify.LOGGER.info(
                f"Finished processing Alert {alert.detection_id}",
                alert_id=alert.detection_id,
            )

        if not is_test_run:
            save_timestamp(siemplify=siemplify, alerts=fetched_alerts)
            write_ids(siemplify, existing_ids, stored_ids_limit=MAX_IDS)

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
    time_passed_from_first_detected_in_minutes = (
        convert_datetime_to_unix_time(utc_now()) - alert.first_timestamp
    ) / 60000
    if (
        time_passed_from_first_detected_in_minutes
        <= ACCEPTABLE_TIME_INTERVAL_IN_MINUTES
    ):
        siemplify.LOGGER.info(
            "Alert did not pass time filter. Detected approximately"
            f" {str(time_passed_from_first_detected_in_minutes)} minutes ago."
        )
        return False
    return True


def pass_whitelist_filter(siemplify, alert, whitelist, whitelist_filter_type):
    # whitelist filter
    if whitelist:
        if (
            whitelist_filter_type == BLACKLIST_FILTER
            and alert.detection_type in whitelist
        ):
            siemplify.LOGGER.info(
                "Threat with name:"
                f" {alert.detection_type} did not pass blacklist filter."
            )
            return False

        if (
            whitelist_filter_type == WHITELIST_FILTER
            and alert.detection_type not in whitelist
        ):
            siemplify.LOGGER.info(
                "Threat with name:"
                 f" {alert.detection_type} did not pass whitelist filter."
            )
            return False

    return True


if __name__ == "__main__":
    # Connectors are run in iterations. 
    # The interval is configurable from the ConnectorsScreen UI.
    is_test = not (len(sys.argv) < 2 or sys.argv[1] == "True")
    main(is_test)
