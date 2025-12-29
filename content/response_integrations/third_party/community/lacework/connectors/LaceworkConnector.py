from __future__ import annotations

import sys
import uuid

from soar_sdk.SiemplifyConnectors import SiemplifyConnectorExecution
from soar_sdk.SiemplifyConnectorsDataModel import AlertInfo
from soar_sdk.SiemplifyUtils import (
    convert_string_to_unix_time,
    dict_to_flat,
    output_handler,
)

from ..core.LaceworkManager import LaceworkManager

CONNECTOR_NAME = "Lacework"
VENDOR = "Lacework"
PRODUCT = "Lacework"
DAY_IN_SECONDS = 86400


@output_handler
def main(is_test_run):
    alerts = []  # The main output of each connector run
    siemplify = SiemplifyConnectorExecution()  # Siemplify main SDK wrapper
    siemplify.script_name = CONNECTOR_NAME

    if is_test_run:
        siemplify.LOGGER.info(
            '***** This is an "IDE Play Button"\\"Run Connector once" test run ******',
        )

    # Initialize parameters

    KEY_ID = siemplify.extract_connector_param(param_name="keyId")
    SECRET = siemplify.extract_connector_param(param_name="secret")
    ACCOUNT_NAME = siemplify.extract_connector_param(param_name="accountName")
    SEVERITY_THRESHOLD = siemplify.extract_connector_param(
        param_name="severity_threshold",
    )

    manager = LaceworkManager(key_id=KEY_ID, secret=SECRET, account_name=ACCOUNT_NAME)
    token = manager.get_temp_token()
    events_list = manager.get_events_for_date_range(token)

    if events_list is None:
        siemplify.LOGGER.info("No events were retrieved from Lacework")
    else:
        siemplify.LOGGER.info(f"Retrieved {len(events_list)} events from Lacework")

    for event in events_list:
        try:
            alert_id = event["EVENT_ID"]

            lacework_severity = event["SEVERITY"]

            # Determine if event should be processed based on severity threshold set in the configuration
            if int(lacework_severity) > int(SEVERITY_THRESHOLD):
                siemplify.LOGGER.info(
                    f"Event Severity: {lacework_severity}. Threshold: less than {SEVERITY_THRESHOLD}. Skipping Event {alert_id}",
                )
                continue
            detailed_alert = manager.get_event_details(alert_id, token)

            # Map the severity in Lacework to the severity levels in Siemplify
            severity = get_siemplify_mapped_severity(lacework_severity)
            siemplify_alert = build_alert_info(siemplify, detailed_alert, severity)

            if siemplify_alert:
                alerts.append(siemplify_alert)
                siemplify.LOGGER.info(f"Added alert {alert_id} to package results")

        except Exception as e:
            siemplify.LOGGER.error(f"Failed to process alert {alert_id}")
            siemplify.LOGGER.exception(e)

    siemplify.return_package(alerts)


def get_siemplify_mapped_severity(severity):
    severity_map = {"1": "100", "2": "80", "3": "60", "4": "40", "5": "-1"}
    return severity_map.get(severity)


def build_alert_info(siemplify, alert, severity):
    """Returns an alert, which is an aggregation of basic events."""
    alert_info = AlertInfo()

    # Each alert_info has a unique key composed of alert_info.name+alert_info.display_id. This key is used to validate data is digested only once by the Siemplify System - to avoid duplicates.
    # If an alert_info has a uniqe_key that has already been digested, it will be ignored.
    # The uniqueness must be persistent, even after server restart\ refetching of the same alert, multiple runs of the same API queries, etc.
    alert_info.display_id = alert["EVENT_ID"]
    alert_info.ticket_id = str(
        uuid.uuid4(),
    )  # In default, ticket_id = display_id. But, if for some reason the external alert id, is different then the composite's key display_id, you can save the original external alert id in this "ticket_id" field.
    alert_info.name = "Lacework Event: " + alert["EVENT_TYPE"]
    alert_info.rule_generator = alert[
        "EVENT_MODEL"
    ]  # Describes the name of the siem's rule, that caused the aggregation of the alert.
    alert_info.start_time = convert_string_to_unix_time(
        alert["START_TIME"],
    )  # Times should be saved in UnixTime. You may use SiemplifyUtils.convert_datetime_to_unix_time, or SiemplifyUtils.convert_string_to_datetime
    alert_info.end_time = convert_string_to_unix_time(
        alert["END_TIME"],
    )  # Times should be saved in UnixTime. You may use SiemplifyUtils.convert_datetime_to_unix_time, or SiemplifyUtils.convert_string_to_datetime
    alert_info.priority = (
        severity  # Informative = -1,Low = 40,Medium = 60,High = 80,Critical = 100.
    )
    alert_info.device_vendor = VENDOR  # This field, may be fetched from the Original Alert. If you build this alert manualy, Describe the source vendor of the data. (ie: Microsoft, Mcafee)
    alert_info.device_product = PRODUCT  # This field, may be fetched from the Original Alert. If you build this alert manualy, Describe the source product of the data. (ie: ActiveDirectory, AntiVirus)
    alert_info.environment = (
        siemplify.context.connector_info.environment
    )  # This field, gets the Environment of the specific connector execution.
    alert_info.events.append(dict_to_flat(alert))
    # ----------------------------- Alert Fields initilization END -----------------------------

    return alert_info


def get_rule_name(rules_list):
    rules_set = set()
    for rule in rules_list:
        rules_set.add(rule["RULE_TITLE"])
    if len(rules_set) == 1:
        return list(rules_set)[0]
    return "Lacework: Multiple rules triggered"


if __name__ == "__main__":
    # Connectors are run in iterations. The interval is configurable from the ConnectorsScreen UI.
    is_test_run = not (len(sys.argv) < 2 or sys.argv[1] == "True")
    main(is_test_run)
