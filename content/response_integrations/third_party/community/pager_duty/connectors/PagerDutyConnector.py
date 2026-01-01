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

from ..core.PagerDutyManager import PagerDutyManager

CONNECTOR_NAME = "PagerDuty"
VENDOR = "PagerDuty"
PRODUCT = "PagerDuty"


@output_handler
def main(is_test_run):
    processed_alerts = []  # The main output of each connector run
    siemplify = SiemplifyConnectorExecution()  # Siemplify main SDK wrapper
    siemplify.script_name = CONNECTOR_NAME

    if is_test_run:
        siemplify.LOGGER.info(
            '***** This is an "IDE Play Button"\\"Run Connector once" test run ******',
        )

    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    api_key = siemplify.extract_connector_param(param_name="apiKey")
    acknowledge_enabled = siemplify.extract_connector_param(param_name="acknowledge")

    siemplify.LOGGER.info("------------------- Main - Started -------------------")
    manager = PagerDutyManager(api_key)

    try:
        incidents_list = manager.list_incidents()
        if incidents_list is None:
            siemplify.LOGGER.info(
                "No events were retrieved for the specified timeframe from PagerDuty",
            )
            return
        siemplify.LOGGER.info(f"Retrieved {len(incidents_list)} events from PagerDuty")
        for incident in incidents_list:
            alert_id = incident["incident_key"]
            # Map the severity in PagerDuty to the severity levels in Siemplify
            severity = get_siemplify_mapped_severity(incident["urgency"])

            siemplify_alert = build_alert_info(siemplify, incident, severity)

            if siemplify_alert:
                processed_alerts.append(siemplify_alert)
                siemplify.LOGGER.info(f"Added incident {alert_id} to package results")
                # `acknowledge_enabled` is a str, hence the str comparison below
                if acknowledge_enabled:
                    incident_got = manager.acknowledge_incident(alert_id)
                    siemplify.LOGGER.info(
                        f"Incident {incident_got} acknowledged in PagerDuty",
                    )
    except Exception as e:
        siemplify.LOGGER.error(
            "There was an error fetching or acknowledging incidents in PagerDuty",
        )
        siemplify.LOGGER.exception(e)

    siemplify.LOGGER.info("------------------- Main - Finished -------------------")
    siemplify.return_package(processed_alerts)


def get_siemplify_mapped_severity(severity):
    severity_map = {"high": "100", "low": "-1"}
    return severity_map.get(severity)


def build_alert_info(siemplify, incident, severity):
    """Returns an alert, which is an aggregation of basic events."""
    alert_info = AlertInfo()
    alert_info.display_id = incident["id"]
    alert_info.ticket_id = str(uuid.uuid4())
    alert_info.name = "PagerDuty Incident: " + incident["title"]
    alert_info.rule_generator = incident["first_trigger_log_entry"]["summary"]
    alert_info.start_time = convert_string_to_unix_time(incident["created_at"])
    alert_info.end_time = alert_info.start_time
    alert_info.severity = severity
    alert_info.device_vendor = VENDOR
    alert_info.device_product = PRODUCT
    alert_info.environment = siemplify.context.connector_info.environment
    alert_info.events.append(dict_to_flat(incident))

    return alert_info


if __name__ == "__main__":
    is_test_run = len(sys.argv) > 2 and sys.argv[1] == "True"
    main(is_test_run)
