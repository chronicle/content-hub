from __future__ import annotations

import time
import uuid

from soar_sdk.SiemplifyConnectors import SiemplifyConnectorExecution
from soar_sdk.SiemplifyConnectorsDataModel import AlertInfo
from soar_sdk.SiemplifyUtils import output_handler, unix_now
from TIPCommon.extraction import extract_connector_param

from ..core.adapter import PlaybookAdapter
from ..core.config import Config
from ..core.utils_manager import GIBConnector


@output_handler
def main():
    # Google Chronicle base class initialization
    siemplify = SiemplifyConnectorExecution()

    # Google Chronicle base class set up
    siemplify.script_name = Config.GC_IP_CONNECTOR_SCRIPT_NAME

    # Get basic alert configuration
    alert_name = extract_connector_param(siemplify, param_name="Case name", print_value=True)
    alert_type = extract_connector_param(siemplify, param_name="Case type", print_value=True)
    alert_severity = extract_connector_param(
        siemplify, param_name="Case severity", print_value=True
    )
    start_date = extract_connector_param(siemplify, param_name="Start date", print_value=True)

    # Create alerts holder (The main output of each connector run)
    alerts = []

    # Generate alert id
    alert_id = str(uuid.uuid4())

    try:
        alert_instance = fetch_alert(
            siemplify=siemplify,
            alert_id=alert_id,
            alert_name=alert_name,
            alert_type=alert_type,
            alert_severity=alert_severity,
            event_start_date=start_date,
        )

        if alert_instance:
            alerts.append(alert_instance)
            siemplify.LOGGER.info("Added Alert {} to package results".format(alert_id))

    except Exception as e:
        siemplify.LOGGER.error("Failed to process Alert {}".format(alert_id), alert_id=alert_id)
        siemplify.LOGGER.exception(e)

    if alerts:
        siemplify.LOGGER.info("Alert was successfully created.")
        siemplify.LOGGER.info(alerts[0].__dict__)
    siemplify.return_package(alerts)


def fetch_alert(siemplify, alert_id, alert_name, alert_type, alert_severity, event_start_date):
    """Returns an alert, which is an aggregation of basic events. (ie:
    Arcsight's correlation, QRadar's Offense)"""

    siemplify.LOGGER.info("──── ALERT PROCESSING {}".format(alert_id), alert_id=alert_id)

    # Alert class initialization
    alert_info = AlertInfo()

    severity_map = {"Informative": -1, "Low": 40, "Medium": 60, "High": 80, "Critical": 100}

    # Set Alert attributes
    alert_info.display_id = alert_id
    alert_info.ticket_id = alert_id
    alert_info.name = alert_name if alert_name else Config.GC_ALERT_NAME_DEFAULT
    alert_info.rule_generator = alert_type if alert_type else Config.GC_ALERT_TYPE_DEFAULT
    alert_info.start_time = unix_now()
    alert_info.end_time = unix_now()
    alert_info.priority = severity_map.get(alert_severity)
    alert_info.device_vendor = Config.GC_ALERT_VENDOR
    alert_info.device_product = Config.GC_ALERT_PRODUCT
    alert_info.environment = siemplify.context.connector_info.environment

    siemplify.LOGGER.info("──── FETCHING EVENTS")

    try:
        # Gather Portal API events
        parsed_portion = gather_events(siemplify, event_start_date)

        if not parsed_portion:
            return None

        # Extract necessary params from Portal API events
        alert_events = [
            (
                str(uuid.uuid4()),
                _event.get("metadata").get("object-id"),
                _event.get("file_ioc__hash").get("hash")[0],
            )
            for _event in parsed_portion
            if _event.get("file_ioc__hash", {}).get("hash", None)
        ]

        if not alert_events:
            return None

        for alert_event in alert_events:
            siemplify.LOGGER.info(alert_event)

            # Configure events
            dummy_event = fetch_event(alert_info, alert_event)

            # Add configured events to the Alert
            if dummy_event:
                event_id = alert_event[0]
                alert_info.events.append(dummy_event)

                siemplify.LOGGER.info("Added Event {} to Alert {}".format(event_id, alert_id))

    except Exception as e:
        siemplify.LOGGER.error("Failed to process Alert {}".format(alert_id), alert_id=alert_id)
        siemplify.LOGGER.exception(e)

    siemplify.LOGGER.info("──── FETCHING EVENTS END")
    siemplify.LOGGER.info("──── ALERT PROCESSING END")
    return alert_info


def fetch_event(alert_info, alert_event):
    event_id = alert_event[0]
    ioc_hash = alert_event[2]

    event = {
        "StartTime": unix_now(),
        "EndTime": unix_now(),
        "name": alert_info.name + " " + event_id,
        "event_type": "FileHash",  # alert_info.rule_generator,
        "device_product": alert_info.device_product,
        "ioc_hash": ioc_hash,
        "severity": 9,
        # "SourceHostName": "DummyHostSrc",
        # "DestinationHostName": "DummyHostDest",
        # "SourceAddress": "10.0.0." + str(randrange(254)),
        # "DestinationAddress": "55.44.33." + str(randrange(254)),
        # "SourceUserName": "",
        # "DestinationUserName": "",
        # "FileName": ""
    }
    return event


def gather_events(siemplify, start_date):
    # Base collection
    collection = "ioc/common"

    # Get poller
    connector = GIBConnector(siemplify)
    creds = (
        extract_connector_param(siemplify, param_name="API login", print_value=False),
        extract_connector_param(siemplify, param_name="API key", print_value=False),
        extract_connector_param(siemplify, param_name="API URL", print_value=False),
    )
    poller = connector.init_action_poller(creds=creds)

    siemplify.LOGGER.info("──── GATHER SEQUPDATE")

    # Extract sequence update number from storage
    fetched_ts = siemplify.fetch_timestamp(datetime_format=False, timezone=False)
    siemplify.LOGGER.info("fetch_ts: {}".format(fetched_ts))

    if fetched_ts:
        # Get start sequence update number from storage
        init_seq_update = fetched_ts
    else:
        # Set start date 1 day back if None
        if not start_date:
            start_date = PlaybookAdapter.get_default_date(days=1)

        siemplify.LOGGER.info("Start date: {}".format(start_date))

        # Get start sequence update number from API
        _seq_update_dict = poller.get_seq_update_dict(date=start_date, collection_name=collection)
        init_seq_update = _seq_update_dict.get(collection, None)

    siemplify.LOGGER.info("Sequence update number: {}".format(init_seq_update))

    # Create generator
    generator = poller.create_update_generator(
        collection_name=collection, sequpdate=init_seq_update, limit=50
    )

    # Sleep to keep API active
    time.sleep(1)

    siemplify.LOGGER.info("──── PARSE DATA")

    # Parse data
    for portion in generator:
        # parsed_portion = portion.raw_dict.get("items")
        parsed_portion = portion.parse_portion(filter_map=[("hash", [""])], check_existence=True)

        # Sleep to keep API active
        time.sleep(1)

        siemplify.LOGGER.info(parsed_portion)

        # Save sequence update number to the Google Chronicle storage
        siemplify.save_timestamp(
            datetime_format=False, timezone=False, new_timestamp=portion.sequpdate
        )

        return parsed_portion

    return None


if __name__ == "__main__":
    main()
