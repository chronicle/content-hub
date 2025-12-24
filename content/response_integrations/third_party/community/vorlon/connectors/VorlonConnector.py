from __future__ import annotations

import sys

from soar_sdk.SiemplifyConnectors import SiemplifyConnectorExecution
from soar_sdk.SiemplifyConnectorsDataModel import CaseInfo
from soar_sdk.SiemplifyUtils import output_handler, unix_now

from ..core.VorlonManager import VorlonManager

# CONSTANTS
CONNECTOR_NAME = "Vorlon Connector"
VENDOR = "Vorlon"
PRODUCT = "Vorlon"
DAY_IN_SECONDS = 86400


def create_case(siemplify, created_event, alert_id):
    siemplify.LOGGER.info(
        f"-------------- Started processing Case {alert_id} --------------",
    )

    case_info = CaseInfo()
    case_info.events = []
    case_info.display_id = created_event.get("id")
    case_info.ticket_id = alert_id
    case_info.name = created_event.get("name")
    case_info.rule_generator = created_event.get("name")
    case_info.start_time = created_event.get("StartTime")
    case_info.end_time = created_event.get("EndTime")
    # alert_info.priority = 60  # Informative = -1,Low = 40,Medium = 60,High = 80,Critical = 100.
    case_info.device_vendor = VENDOR
    case_info.device_product = PRODUCT
    case_info.environment = siemplify.context.connector_info.environment
    case_info.events.append(created_event)
    siemplify.LOGGER.info("--- Finished processing Case {alert_id} ---")
    return case_info


def create_event(siemplify, fetched_alert):
    siemplify.LOGGER.info("--- Started processing Event -----")
    event = {}
    event["StartTime"] = int(fetched_alert.get("created")) * 1000
    event["EndTime"] = int(fetched_alert.get("created")) * 1000
    event["name"] = fetched_alert.get("title") + " " + str(fetched_alert.get("id"))
    event["device_product"] = PRODUCT
    event["id"] = fetched_alert.get("id")

    event["description"] = fetched_alert.get("description")
    event["status"] = fetched_alert.get("status")
    event["requesting_service_id"] = fetched_alert.get("requesting_service").get(
        "service_id",
        "",
    )
    event["requesting_service_name"] = fetched_alert.get("requesting_service").get(
        "name",
        "",
    )
    event["requesting_service_host"] = fetched_alert.get("requesting_service").get(
        "host",
        "",
    )
    event["responding_service_id"] = fetched_alert.get("responding_service").get(
        "service_id",
        "",
    )
    event["responding_service_name"] = fetched_alert.get("responding_service").get(
        "name",
        "",
    )
    event["responding_service_instance"] = fetched_alert.get("responding_service").get(
        "instance",
        "",
    )
    event["secret_type"] = (
        fetched_alert.get("secret_type") if fetched_alert.get("secret_type") else ""
    )
    event["secret_id"] = (
        fetched_alert.get("secret_id") if fetched_alert.get("secret_id") else ""
    )
    event["severity"] = (
        fetched_alert.get("severity") if fetched_alert.get("severity") else ""
    )

    siemplify.LOGGER.info("--- Finished processing Event ----")

    return event


def fetch_last_saved_timestamp(siemplify, time_now, max_days_backwards):
    last_saved_timestamp = siemplify.fetch_timestamp()
    if last_saved_timestamp > 0 and not is_test_run:
        last_saved_timestamp = int(last_saved_timestamp / 1000)
        siemplify.LOGGER.info(f"The last timestamp:{last_saved_timestamp}")

    else:
        last_saved_timestamp = int(time_now / 1000) - (
            max_days_backwards * DAY_IN_SECONDS
        )
        siemplify.LOGGER.info(
            f"There is no timestamp to fetch, the new timestamp is:{last_saved_timestamp}",
        )
    return last_saved_timestamp


@output_handler
def main(is_test_run):
    cases = []
    siemplify = SiemplifyConnectorExecution()
    siemplify.script_name = CONNECTOR_NAME
    collected_timestamps = []

    if is_test_run:
        siemplify.LOGGER.info(
            '***** This is an "IDE Play Button"\\"Run Connector once" test run ******',
        )

    siemplify.LOGGER.info("==================== Main - Param Init ====================")

    api_root = siemplify.extract_connector_param(param_name="API Root")
    client_id = siemplify.extract_connector_param(param_name="Client ID")
    client_secret = siemplify.extract_connector_param(param_name="Client Secret")
    alert_status = siemplify.extract_connector_param(param_name="Open Alerts Only")
    max_incidents = siemplify.extract_connector_param(
        param_name="Max Incidents per Fetch",
    )
    max_days_backwards = siemplify.extract_connector_param(
        param_name="Max Days Backwards",
    )

    siemplify.LOGGER.info("------------------- Main - Started -------------------")

    # Alert status
    status = "open" if alert_status else "open,dismissed,resolved"

    # Handle Time
    time_now = unix_now()

    last_saved_timestamp = fetch_last_saved_timestamp(
        siemplify,
        time_now,
        int(max_days_backwards),
    )

    # Get Vorlon Alerts
    page = 0
    manager = VorlonManager(
        url=api_root,
        client_id=client_id,
        client_secret=client_secret,
    )
    fetched_alerts = manager.get_alerts(
        from_time=last_saved_timestamp,
        status=status,
        limit=max_incidents,
        page=page,
    )
    has_more = True
    while has_more:
        if len(fetched_alerts) > 0:
            # Testing on one incident
            if is_test_run:
                siemplify.LOGGER.info(
                    "This is a TEST run. Only 5 alert will be processed.",
                )
                fetched_alerts = fetched_alerts[:5]

            if len(fetched_alerts) < int(max_incidents):
                has_more = False

            siemplify.LOGGER.info(f"Fetched {len(fetched_alerts)} alerts")
            for fetched_alert in fetched_alerts:
                alert_id = fetched_alert.get("id")
                # Create Event
                created_event = create_event(siemplify, fetched_alert)
                created_case = create_case(siemplify, created_event, alert_id)
                if created_case is not None:
                    collected_timestamps.append(fetched_alert.get("created"))
                    cases.append(created_case)
                    siemplify.LOGGER.info(f"Added Alert {alert_id} to package results")
                else:
                    siemplify.LOGGER.info("No new alerts were found")
            if has_more:
                page = page + 1
                fetched_alerts = manager.get_alerts(
                    from_time=last_saved_timestamp,
                    status=status,
                    limit=max_incidents,
                    page=page,
                )
        else:
            collected_timestamps.append(unix_now())
            has_more = False
            siemplify.LOGGER.info("There are no new alerts from Vorlon")

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
        siemplify.return_package(cases)


if __name__ == "__main__":
    # Connectors are run in iterations. The interval is configurable from the ConnectorsScreen UI.
    is_test_run = not (len(sys.argv) < 2 or sys.argv[1] == "True")
    main(is_test_run)
