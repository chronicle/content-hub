from __future__ import annotations

import sys

from greynoise import GreyNoise
from greynoise.exceptions import RequestFailure
from soar_sdk.SiemplifyConnectors import SiemplifyConnectorExecution
from soar_sdk.SiemplifyConnectorsDataModel import AlertInfo
from soar_sdk.SiemplifyUtils import output_handler, unix_now

from ..core.constants import USER_AGENT

CONNECTOR_NAME = "GreyNoise GNQL Connector"
VENDOR = "GreyNoise"
PRODUCT = "GreyNoise"


@output_handler
def main(is_test_run):
    alerts = []
    siemplify = SiemplifyConnectorExecution()
    siemplify.script_name = CONNECTOR_NAME

    if is_test_run:
        siemplify.LOGGER.info(
            '***** This is an "IDE Play Button Run Connector once" test run ******',
        )

    siemplify.LOGGER.info("==================== Main - Param Init ====================")

    query = siemplify.extract_connector_param("query", print_value=True)
    limit = siemplify.extract_connector_param(
        "limit",
        default_value="10",
        is_mandatory=False,
        print_value=True,
    )
    api_key = siemplify.extract_connector_param("GN API Key", print_value=False)

    session = GreyNoise(api_key=api_key, integration_name=USER_AGENT)

    siemplify.LOGGER.info("------------------- Main - Started -------------------")

    try:
        res = session.query(query=query, size=limit)

        if res and res["count"] > 0:
            output = res

            for result in output["data"]:
                datetime_in_unix_time = unix_now()
                alert_id = str(datetime_in_unix_time) + "-" + result["ip"]

                # Creating the event by calling create_event() function
                created_event = create_event(
                    siemplify,
                    alert_id,
                    result,
                    datetime_in_unix_time,
                )
                # Creating the alert by calling create_alert() function
                created_alert = create_alert(
                    siemplify,
                    alert_id,
                    result,
                    datetime_in_unix_time,
                    created_event,
                )

                # Checking that the created_alert is not None
                if created_alert is not None:
                    alerts.append(created_alert)
                    siemplify.LOGGER.info(f"Added Alert {alert_id} to package results")
    except RequestFailure as e:
        if "401" in str(e):
            siemplify.LOGGER.error(
                "Unable to auth, please check API Key.  This action requires a Paid Subscription.",
            )
        else:
            siemplify.LOGGER.error(f"There was an issue with your query: {e}")
        siemplify.LOGGER.exception(e)

    except Exception as e:
        siemplify.LOGGER.error(f"Failed to process alert {alert_id}", alert_id=alert_id)
        siemplify.LOGGER.exception(e)

    siemplify.LOGGER.info("------------------- Main - Finished -------------------")
    siemplify.return_package(alerts)


def create_alert(siemplify, alert_id, result, datetime_in_unix_time, created_event):
    """Returns an alert which is one event that contains one unread email message"""
    siemplify.LOGGER.info(f"-------------- Started processing Alert {alert_id}")
    alert_info = AlertInfo()

    alert_info.display_id = f"{alert_id}"
    alert_info.ticket_id = f"{alert_id}"
    alert_info.name = (
        str(result["ip"]) + " has been observed mass-scanning the internet"
    )
    alert_info.start_time = datetime_in_unix_time
    alert_info.end_time = datetime_in_unix_time
    alert_info.SourceAddress = result["ip"]
    alert_info.EventTime = result["last_seen"]
    alert_info.rule_generator = "GreyNoise Ingestion"
    alert_info.priority = 60
    alert_info.device_vendor = VENDOR
    alert_info.device_product = PRODUCT

    siemplify.LOGGER.info(f"---------- Events creating started for alert  {alert_id}")
    try:
        if created_event is not None:
            alert_info.events.append(created_event)
        siemplify.LOGGER.info(f"Added Event {alert_id} to Alert {alert_id}")

    except Exception as e:
        siemplify.LOGGER.error(f"Failed to process event {alert_id}")
        siemplify.LOGGER.exception(e)

    return alert_info


def create_event(siemplify, alert_id, result, datetime_in_unix_time):
    """Returns the digested data of a single unread email"""
    siemplify.LOGGER.info(
        f"--- Started processing Event:  alert_id: {alert_id} | event_id: {alert_id}",
    )
    event = {}
    event["StartTime"] = datetime_in_unix_time
    event["EndTime"] = datetime_in_unix_time
    event["event_name"] = "Mass Scanning IP Detected"
    event["device_product"] = PRODUCT

    event["SourceAddress"] = result["ip"]
    event["EventTime"] = result["last_seen"]
    event["Classification"] = result["classification"]

    siemplify.LOGGER.info(
        f"--- Finished processing Event: alert_id: {alert_id} | event_id: {alert_id}",
    )
    return event


if __name__ == "__main__":
    is_test_run = not (len(sys.argv) < 2 or sys.argv[1] == "True")
    main(is_test_run)
