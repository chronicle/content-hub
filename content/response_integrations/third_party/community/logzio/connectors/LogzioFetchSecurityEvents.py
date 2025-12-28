from __future__ import annotations

import concurrent.futures
import datetime
import json
import math

import dateparser
import requests
from soar_sdk.SiemplifyConnectors import SiemplifyConnectorExecution
from soar_sdk.SiemplifyConnectorsDataModel import AlertInfo
from soar_sdk.SiemplifyUtils import output_handler

CONNECTOR_NAME = "fetch-security-events"
PRODUCT = "Logz.io"
VENDOR = "Logz.io"
BASE_URL = "https://api.logz.io/"
TRIGGERED_RULES_API_SUFFIX = "v2/security/rules/events/search"
SORTING_FIELD_INDEX = 0
SORTING_DESCENDING_INDEX = 1
SEVERITIES = {
    "INFO": -1,
    "LOW": 40,
    "MEDIUM": 60,
    "HIGH": 80,
    "SEVERE": 100,
}  # maps logzio severity values to siemplify severities
DEFAULT_PAGE_SIZE = 25
MIN_PAGE_SIZE = 1
MAX_PAGE_SIZE = 1000


@output_handler
def main():
    alerts = []  # The main output of each connector run
    siemplify = SiemplifyConnectorExecution()  # Siemplify main SDK wrapper
    siemplify.script_name = CONNECTOR_NAME

    logzio_api_token = siemplify.extract_connector_param(
        "logzio_token",
        is_mandatory=True,
    )
    if logzio_api_token == "":
        siemplify.LOGGER.error("Error occurred: no Logzio API token! Exiting.")
        raise ValueError
    logzio_region = siemplify.extract_connector_param(
        "logzio_region",
        is_mandatory=False,
        default_value="",
    )
    url = get_logzio_api_endpoint(siemplify, logzio_region)
    events_response = execute_logzio_api(siemplify, logzio_api_token, url)
    if events_response is not None:
        alerts = create_alerts_array(siemplify, events_response, logzio_api_token, url)

    siemplify.LOGGER.info(f"Total {len(alerts)} alerts will be returned to Siemplify")
    siemplify.return_package(alerts)


def create_request_body_obj(siemplify, page_number=1):
    """Creates request to send to Logz.io API"""
    request_body = {}
    from_date, to_date = get_dates(siemplify)
    search_term = siemplify.extract_connector_param("search_term", is_mandatory=False)
    severities = siemplify.extract_connector_param("severities", is_mandatory=False)
    page_size = siemplify.extract_connector_param(
        "page_size",
        is_mandatory=False,
        default_value=DEFAULT_PAGE_SIZE,
        input_type=int,
    )
    if page_size < MIN_PAGE_SIZE or page_size > MAX_PAGE_SIZE:
        siemplify.LOGGER.warning(
            f"Invalid page size. Should be betwwen {MIN_PAGE_SIZE} and {MAX_PAGE_SIZE}. Reverting to default page size: {DEFAULT_PAGE_SIZE}",
        )
        page_size = DEFAULT_PAGE_SIZE
    request_body["filter"] = {}
    request_body["filter"]["timeRange"] = dict(fromDate=from_date, toDate=to_date)
    if search_term != None:
        request_body["filter"]["searchTerm"] = search_term
    if severities != None:
        request_body["filter"]["severities"] = [
            s.strip() for s in severities.split(",")
        ]
    request_body["sort"] = [{"field": "DATE", "descending": False}]
    request_body["pagination"] = dict(pageNumber=page_number, pageSize=page_size)
    siemplify.LOGGER.info(f"{request_body}")
    return request_body


def get_base_api_url(region):
    """Returnes API url, in accordance to user's input"""
    if region == "us" or region == "":
        return BASE_URL
    return BASE_URL.replace("api.", f"api-{region}.")


def fetch_security_events(api_token, req_body, url, siemplify):
    """Returnes security events from Logz.io.
    If error occured or no results found, returnes None
    """
    headers = {"Content-Type": "application/json", "X-API-TOKEN": api_token}

    siemplify.LOGGER.info(f"api url: {url}")
    try:
        body = json.dumps(req_body)
        siemplify.LOGGER.info("Fetching security events from Logz.io")
        response = requests.post(url, headers=headers, data=body, timeout=5)
        siemplify.LOGGER.info(f"Status code from Logz.io: {response.status_code}")
        if response.status_code == 200:
            events_response = json.loads(response.content)
            if events_response["total"] > 0:
                return events_response
            siemplify.LOGGER.warning("No resultes found to match your request")
            return None
        siemplify.LOGGER.error(f"API request returned {response.status_code}")
    except Exception as e:
        siemplify.LOGGER.error(
            f"Error occurred while fetching security events from Logz.io:\n{e}",
        )
        return None


def create_event(siemplify, logzio_event):
    """Returns the digested data of a single Logz.io secutiry event"""
    siemplify.LOGGER.info(
        f"Processing siemplify event for logzio security event: {logzio_event['alertEventId']}",
    )
    event = {}
    try:
        event["StartTime"] = logzio_event["alertWindowStartDate"]
        event["EndTime"] = logzio_event["alertWindowEndDate"]
        event["event_name"] = logzio_event["name"]
        event["device_product"] = (
            PRODUCT  # ie: "device_product" is the field name that describes the product the event originated from.
        )
        event["alertEventId"] = logzio_event["alertEventId"]
        event["description"] = logzio_event["description"]
        event["alertSummary"] = logzio_event["alertSummary"]
        event["eventDate"] = logzio_event["eventDate"]
        event["severity"] = logzio_event["severity"]
        if "groupBy" in logzio_event:
            for k, v in logzio_event["groupBy"].items():
                event[f"groupBy.{k}"] = v
        if "tags" in logzio_event:
            tags_counter = 0
            for tag in logzio_event["tags"]:
                event[f"tags.{tags_counter}"] = tag
                tags_counter += 1
        event["hits"] = logzio_event["hits"]
    except Exception as e:
        siemplify.LOGGER.error(
            f"Error occurred while trying to process logzio event {logzio_event['alertEventId']}:{e}\n Dropping event.",
        )
        return None
    return event


def create_alert(siemplify, event, logzio_event):
    """Returns an alert which is one event that contains one Logz.io secrutiry event"""
    siemplify.LOGGER.info(
        f"Processing siempify alert for logzio security event: {logzio_event['alertId']}",
    )
    alert_info = AlertInfo()

    try:
        alert_info.display_id = logzio_event["alertEventId"]
        alert_info.ticket_id = logzio_event["alertEventId"]
        alert_info.name = logzio_event["name"]
        alert_info.rule_generator = logzio_event["alertSummary"]
        alert_info.start_time = logzio_event["alertWindowStartDate"]
        alert_info.end_time = logzio_event["alertWindowEndDate"]
        alert_info.priority = SEVERITIES[logzio_event["severity"]]
        alert_info.device_vendor = VENDOR
        alert_info.device_product = PRODUCT
    except Exception as e:
        siemplify.LOGGER.error(
            f"Error occurred while trying to add event {logzio_event['alertEventId']} to alert: {e}\n Dropping event.",
        )
        alert_info = None

    siemplify.LOGGER.info(
        f"Creating siempify alert for logzio security event: {logzio_event['alertId']}",
    )
    try:
        if alert_info is not None and event is not None:
            alert_info.events.append(event)
        siemplify.LOGGER.info(
            f"Added Event {logzio_event['alertEventId']} to Alert {logzio_event['alertId']}",
        )
    except Exception as e:
        siemplify.LOGGER.error(
            f"Failed to process event {logzio_event['alertEventId']} for alert {logzio_event['alertId']}",
        )
        siemplify.LOGGER.exception(e)
        return None
    return alert_info


def create_alerts_array(siemplify, events_response, api_token, url):
    """Returns the alerts that will be injected to Siemplify.
    If a query has more results than the page size, the function will request all the relevant
    pages from Logz.io, and only then will create Siemplify events & alerts.
    """
    alerts = []
    collected_events = events_response["results"]
    num_collected_events = len(collected_events)
    total_results_available = int(events_response["total"])
    current_page = int(events_response["pagination"]["pageNumber"])
    num_pages = math.ceil(
        total_results_available / int(events_response["pagination"]["pageSize"]),
    )
    siemplify.LOGGER.info(
        f"Request retrieved {num_collected_events} events from Logz.io",
    )
    siemplify.LOGGER.info(
        f"There are {total_results_available} results in your Logz.io account that match your query",
    )
    with concurrent.futures.ThreadPoolExecutor(max_workers=num_pages) as executor:
        futures = []
        while num_pages > current_page:
            current_page += 1
            print(f"fetching page: {current_page}")
            futures.append(
                executor.submit(
                    execute_logzio_api,
                    siemplify,
                    api_token,
                    url,
                    current_page,
                ),
            )
        for future in concurrent.futures.as_completed(futures):
            new_event = future.result()
            if new_event is not None:
                collected_events += new_event["results"]
                num_collected_events += len(new_event["results"])
                siemplify.LOGGER.info(f"Fetched {len(new_event['results'])} events")

        if total_results_available != num_collected_events:
            siemplify.LOGGER.warning(
                f"Retrieved {num_collected_events} events out of {total_results_available} available events. Only the retrieved events will be injected to Siemplify",
            )
    siemplify.LOGGER.info(f"Total collected: {len(collected_events)}")

    latest_timestamp = siemplify.fetch_timestamp()
    for logzio_event in collected_events:
        event = create_event(siemplify, logzio_event)
        alert = create_alert(siemplify, event, logzio_event)
        if alert is not None:
            alerts.append(alert)
            siemplify.LOGGER.info(
                f"Added Alert {logzio_event['alertId']} to package results",
            )
            current_end_time = int(logzio_event["eventDate"])
            latest_timestamp = max(latest_timestamp, current_end_time)

    save_latest_timestamp(siemplify, latest_timestamp)

    return alerts


def execute_logzio_api(siemplify, api_token, url, page_number=1):
    """Sends request for security events to Logz.io and returnes the response, if applicable"""
    try:
        siemplify.LOGGER.info(f"Fetching page number {page_number}")
        new_request = create_request_body_obj(siemplify, page_number)
        new_events = fetch_security_events(api_token, new_request, url, siemplify)
        if new_events is not None:
            return new_events
    except Exception as e:
        siemplify.LOGGER.error(
            f"Error occurred while fetching events from page {page_number}: {e}",
        )
    return None


def get_dates(siemplify):
    """Returnes start time & end time for fetching security events from Logz.io.
    If it's the first run, the start time will be the start time the user inserted, otherwise
    it will be the latest saved timestamp with offset of +1 millisecond.
    The end date will always be now - 3 min.
    """
    start_time = siemplify.fetch_timestamp()
    siemplify.LOGGER.info(f"Fetched timestamp: {start_time}")
    if start_time == 0:
        # first run
        siemplify.LOGGER.info("No saved latest timestamp. Using user's input.")
        start_time_str = siemplify.extract_connector_param(
            "from_date",
            is_mandatory=True,
        )
        if not start_time_str.isdigit():
            start_time = datetime.datetime.timestamp(
                dateparser.parse(
                    start_time_str,
                    date_formats=["%Y-%m-%dT%H:%M:%S.%f"],
                    settings={"TIMEZONE": "UTC"},
                ),
            )
        else:
            start_time = start_time_str
    else:
        milliseconds_delta = datetime.timedelta(milliseconds=100)
        start_time = (
            datetime.datetime.fromtimestamp(start_time) + milliseconds_delta
        ).timestamp()
    end_time_delta = datetime.timedelta(minutes=3)
    now = datetime.datetime.now()
    end_time_datetime = now - end_time_delta
    end_time = end_time_datetime.timestamp()
    return str(start_time), str(end_time)


def save_latest_timestamp(siemplify, latest_timestamp_from_events):
    """Saves the latest timestamp.
    Latest timestamp will be the latest between the two: now - hour, or timestamp of latest event.
    """
    hour_ago_delta = datetime.timedelta(hours=1)
    hour_ago = (datetime.datetime.now() - hour_ago_delta).timestamp()
    latest = max(latest_timestamp_from_events, int(hour_ago))
    siemplify.LOGGER.info(f"Latest timestamp to save: {latest}")
    siemplify.save_timestamp(new_timestamp=latest)


def get_logzio_api_endpoint(siemplify, region):
    """Returns the endpoint of Logz.io API.
    Prioritizing a custom endoint, if entered.
    If not, falling back to the regaular enspoints, based on the logzio_region (defaults to us).
    """
    custom_endpoint = siemplify.extract_connector_param(
        "logzio_custom_endpoint",
        is_mandatory=False,
        default_value="",
    )
    if custom_endpoint is not None and custom_endpoint != "":
        siemplify.LOGGER.info(f"Using custom endpoint: {custom_endpoint}")
        return custom_endpoint + TRIGGERED_RULES_API_SUFFIX
    return get_base_api_url(region) + TRIGGERED_RULES_API_SUFFIX


if __name__ == "__main__":
    main()
