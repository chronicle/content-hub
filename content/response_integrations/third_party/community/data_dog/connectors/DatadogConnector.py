from __future__ import annotations

import json
import re
import sys
import time

from soar_sdk.SiemplifyConnectors import SiemplifyConnectorExecution
from soar_sdk.SiemplifyConnectorsDataModel import AlertInfo
from soar_sdk.SiemplifyUtils import dict_to_flat, output_handler

from ..core.DataDogManager import DataDogManager, dict_to_flat

# CONSTANTS
IDENTIFIER = "DataDog"
CONNECTOR_NAME = "DataDog Connector"
VENDOR = PRODUCT = "DataDog"
DEFAULT_PRIORITY = {"error": 100, "warning": 80, "ok": -1}
BASE_URL = "https://api.datadoghq.com"
REGEX_VALUE_BEFORE_COLON = r"^[^:]*\s*"
REGEX_VALUE_AFTER_COLON = "[^:]*$"
DAY_IN_SECONDS = 86400


def create_alert(siemplify, created_event, base_url):
    """Create the alert and ingest it into the platform"""
    alert_id = created_event.get("id")
    siemplify.LOGGER.info(f"-------Started processing Alert {alert_id}-------")
    alert_info = AlertInfo()

    # Initializes the alert_info Characteristics Fields
    alert_info.ticket_id = alert_id
    alert_info.display_id = alert_id  # Each alert needs to have a unique id, otherwise it won't  create a case with the same alert id.
    alert_info.name = created_event.get("monitor_name")
    alert_info.rule_generator = created_event.get(
        "metric",
    )  # The name of the siem rule which causes the creation of the alert.
    alert_info.start_time = created_event.get(
        "date_happened",
    )  # Time should be saved in UnixTime. You may use SiemplifyUtils.convert_datetime_to_unix_time, or SiemplifyUtils.convert_string_to_datetime
    alert_info.end_time = created_event.get(
        "date_happened",
    )  # Time should be saved in UnixTime. You may use SiemplifyUtils.convert_datetime_to_unix_time, or SiemplifyUtils.convert_string_to_datetime
    alert_info.priority = DEFAULT_PRIORITY.get(created_event.get("alert_type"), -1)
    alert_info.device_vendor = VENDOR  # The field will be fetched from the Original Alert. If you build this alert manually, state the source vendor of the data. (ie: Microsoft, Mcafee)
    alert_info.device_product = created_event.get(
        "device_product",
    )  # The field will be fetched from the Original Alert. If you build this alert manually, state the source product of the data. (ie: ActiveDirectory, AntiVirus)
    alert_info.events.append(created_event)
    return alert_info


def create_event(siemplify, event_full_details, base_url):
    """Returns the digested data of a single alert triggered by a monitor"""
    event = {}
    product_name = "Product name wasn't found"
    # Extracting the tag key and value e.g pod_name:podnameexample
    if event_full_details.get("event").get("tags") is not None:
        for tag in event_full_details.get("event").get("tags"):
            tag_key = (re.search(REGEX_VALUE_BEFORE_COLON, tag)).group(0)
            tag_value = (re.search(REGEX_VALUE_AFTER_COLON, tag)).group(0)
            event[tag_key] = tag_value
    # Extracting the metric field from payload
    event = dict_to_flat(event_full_details.get("event"))
    event_payload = json.loads(event_full_details.get("event").get("payload"))
    event_monitor_name = event_payload.get("monitor").get("name")
    # Extracting the even metric name
    event_metric = event_payload.get("result").get("metadata").get("metric")

    # Extracting the product name depends on the event metric name.
    if event_metric is not None:
        event_metric_list = event_metric.split(".")
        if event_metric_list[0] == "aws":
            product_name = f"{event_metric_list[0]} {event_metric_list[1]}"
        else:
            product_name = event_metric_list[0]
    else:
        event_metric = product_name = event_monitor_name

    siemplify.LOGGER.info(
        f"-------Started processing the Event {event_payload.get('monitor').get('name')}-------",
    )

    event["metric"] = event_metric
    event["monitor_id"] = event_payload.get("monitor").get("id")
    event["monitor_name"] = event_monitor_name
    event["alert_url"] = f"{base_url}" + event_payload.get("result").get(
        "metadata",
    ).get("alert_url")
    event["graph_snapshot_url"] = (
        event_payload.get("result").get("metadata").get("snap_url")
    )
    event["device_product"] = (
        product_name  # ie: "device_product" is the field name that describes the product the event originated from.
    )
    event["url"] = f"{base_url}{event.get('url')}"
    event["start_time"] = event_full_details.get("event").get(
        "date_happened",
    )  # Time should be saved in UnixTime. You may use SiemplifyUtils.convert_datetime_to_unix_time, or SiemplifyUtils.convert_string_to_datetime
    event["end_time"] = event_full_details.get("event").get(
        "date_happened",
    )  # Time should be saved in UnixTime. You may use SiemplifyUtils.convert_datetime_to_unix_time, or SiemplifyUtils.convert_string_to_datetime
    event["event_name"] = event_payload.get("monitor").get("name")
    return event


def fetch_last_saved_timestamp(siemplify, time_now, max_days_back):
    last_saved_timestamp = siemplify.fetch_timestamp()
    if last_saved_timestamp > 0 and not is_test_run:
        last_saved_timestamp = int(last_saved_timestamp / 1000)
        siemplify.LOGGER.info(
            f"This is a real run. The last timestamp that was saved is:{last_saved_timestamp}",
        )

    else:
        last_saved_timestamp = time_now - (max_days_back * DAY_IN_SECONDS)
        siemplify.LOGGER.info(
            f"There is no timestamp to fetch, the new timestamp is:{last_saved_timestamp}",
        )
    return last_saved_timestamp


@output_handler
def main(is_test_run):
    siemplify = SiemplifyConnectorExecution()  # Siemplify main SDK wrapper
    siemplify.script_name = CONNECTOR_NAME
    alerts = []  # The main output of each connector run that contains the alerts data
    collected_timestamps = []
    # In case of running a test
    if is_test_run:
        siemplify.LOGGER.info(
            '***** This is an "IDE Play Button"\\"Run Connector once" test run ******',
        )
    # Extracting the connector's params
    api_key = siemplify.extract_connector_param(param_name="API Key")
    app_key = siemplify.extract_connector_param(param_name="APP Key")
    sources = siemplify.extract_connector_param(param_name="Sources")
    tags = siemplify.extract_connector_param(param_name="Tags")
    priority = siemplify.extract_connector_param(param_name="Priority")
    unaggregated = siemplify.extract_connector_param(
        param_name="Unaggregated",
        input_type=bool,
    )
    max_days_back = siemplify.extract_connector_param(
        param_name="Max Days Back",
        input_type=int,
    )
    base_url = siemplify.extract_connector_param(param_name="Base URL")

    # Creating an instance of DataDog object
    datadog_manager = DataDogManager(api_key, app_key)
    time_now = int(time.time())

    last_saved_timestamp = fetch_last_saved_timestamp(
        siemplify,
        time_now,
        max_days_back,
    )

    # Get all the new triggered error alerts from all monitors
    events_data = datadog_manager.get_datadog_events(
        last_saved_timestamp,
        time_now,
        sources,
        tags,
        priority,
        unaggregated,
    )
    if len(events_data.get("events")) > 0:
        for i, event_parent_data in enumerate(events_data.get("events")):
            if event_parent_data.get("date_happened") > last_saved_timestamp:
                parent_alert_type = event_parent_data.get("alert_type")
                if parent_alert_type == "error" or parent_alert_type == "warning":
                    siemplify.LOGGER.info(
                        f"The event parent ID is:{event_parent_data.get('id')}",
                    )
                    if event_parent_data.get("children") is not None:
                        # If the event has children events, each of the children events will be considered as an alert
                        siemplify.LOGGER.info(
                            f"The event {event_parent_data.get('id')} has related children events:\n{event_parent_data.get('children')}",
                        )
                        for event in event_parent_data.get("children"):
                            event_full_details = datadog_manager.get_event_details(
                                event.get("id"),
                            )
                            siemplify.LOGGER.info(
                                f"The event children {event.get('id')} full data is retrieved sucessfully",
                            )
                            # Creating the event
                            created_event = create_event(
                                siemplify,
                                event_full_details,
                                base_url,
                            )
                            # siemplify.LOGGER.info(f"The event children {event.get('id')} was created as Event in Siemplify")
                            # Creating the alert
                            created_alert = create_alert(
                                siemplify,
                                created_event,
                                base_url,
                            )
                            siemplify.LOGGER.info(
                                f"The event children {event.get('id')} was created as Alert in Siemplify",
                            )
                            alerts.append(created_alert)
                            siemplify.LOGGER.info(
                                f"Added Alert {created_alert.display_id} to package results",
                            )
                            collected_timestamps.append(event.get("date_happened"))

                    else:
                        siemplify.LOGGER.info(
                            f"The event {event_parent_data.get('id')} has not related children events.",
                        )
                        collected_timestamps.append(
                            event_parent_data.get("date_happened"),
                        )
                        # If the event doesn't have children events we will get the parent event
                        event_full_details = datadog_manager.get_event_details(
                            event_parent_data.get("id"),
                        )
                        # Creating the event
                        created_event = create_event(
                            siemplify,
                            event_full_details,
                            base_url,
                        )
                        # Creating the alert
                        created_alert = create_alert(siemplify, created_event, base_url)
                        alerts.append(created_alert)
                        siemplify.LOGGER.info(
                            f"Added Alert {created_alert.display_id} to package results",
                        )

    else:
        siemplify.LOGGER.info("There are no new events to digest")

    if not is_test_run:
        siemplify.LOGGER.info(
            f"The timestamps that were collected are: {collected_timestamps}",
        )
        siemplify.LOGGER.info(
            f"The latest timestamp to save is {max(collected_timestamps)}",
        )
        new_timestamp_to_save = max(collected_timestamps)
        siemplify.save_timestamp(new_timestamp_to_save)
        siemplify.LOGGER.info(
            f"The new timestamp that was saved: {new_timestamp_to_save}.",
        )

    # Returning all the created alerts to the cases module in Siemplify
    siemplify.return_package(alerts)


if __name__ == "__main__":
    # Connectors run in iterations. The interval is configurable from the ConnectorsScreen UI.
    is_test_run = not (len(sys.argv) < 2 or sys.argv[1] == "True")
    main(is_test_run)
