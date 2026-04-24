from __future__ import annotations
import uuid
import time
from datetime import datetime, timedelta, timezone
from urllib.parse import urljoin, urlencode

from soar_sdk.SiemplifyConnectors import SiemplifyConnectorExecution
from soar_sdk.SiemplifyConnectorsDataModel import AlertInfo
from soar_sdk.SiemplifyUtils import output_handler, unix_now

from TIPCommon.extraction import extract_connector_param

# Import Managers
from ..core.config import Config
from ..core.UtilsManager import GIBConnector, extract_host


def get_default_date(days=1):
    return (datetime.now(tz=timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")


@output_handler
def main():
    siemplify = SiemplifyConnectorExecution()
    siemplify.script_name = Config.GC_TYPOSQUATTING_CONNECTOR_SCRIPT_NAME

    alert_name = extract_connector_param(siemplify, param_name="Case name", print_value=True)
    alert_type = extract_connector_param(siemplify, param_name="Case type", print_value=True)
    alert_severity = extract_connector_param(siemplify, param_name="Case severity", print_value=True)
    start_date = extract_connector_param(siemplify, param_name="Start date", print_value=True)

    alerts = []

    try:
        parsed_portion = gather_events(siemplify, start_date)

        if parsed_portion:
            for _event in parsed_portion:
                uid = _event.get("uid")
                fake_uri = _event.get("fake_uri")

                if not uid or not fake_uri:
                    siemplify.LOGGER.info("Skipped event — uid={} fake_uri={}".format(uid, fake_uri))
                    continue

                alert_instance = create_alert(
                    siemplify=siemplify,
                    uid=uid,
                    fake_uri=fake_uri,
                    alert_name=alert_name,
                    alert_type=alert_type,
                    alert_severity=alert_severity
                )

                if siemplify.is_overflowed_alert(
                    environment=siemplify.context.connector_info.environment,
                    alert_identifier=alert_instance.display_id,
                    ingestion_time=unix_now(),
                    alert_name=alert_instance.name,
                    product=Config.GC_ALERT_PRODUCT,
                ):
                    siemplify.LOGGER.info("Alert {} overflowed. Skipping this run.".format(uid))
                    continue

                siemplify.LOGGER.info("Created alert — display_id={} source_grouping_identifier={} url={}".format(
                    alert_instance.display_id,
                    alert_instance.source_grouping_identifier,
                    fake_uri
                ))
                alerts.append(alert_instance)

    except Exception as e:
        siemplify.LOGGER.error("Failed to process violations")
        siemplify.LOGGER.exception(e)

    siemplify.LOGGER.info("Returning {} alert(s) to package".format(len(alerts)))
    siemplify.return_package(alerts)


def create_alert(siemplify, uid, fake_uri, alert_name, alert_type, alert_severity):
    """Creates one AlertInfo per violation."""

    severity_map = {
        "Informative": -1,
        "Low": 40,
        "Medium": 60,
        "High": 80,
        "Critical": 100
    }

    prefix = alert_name if alert_name else Config.GC_ALERT_NAME_DEFAULT
    type_prefix = alert_type if alert_type else Config.GC_ALERT_TYPE_DEFAULT
    host = extract_host(fake_uri, fallback=uid)
    display_name = "{}: {}".format(prefix, host)

    alert_info = AlertInfo()
    alert_info.display_id                 = str(uuid.uuid4())  # unique per ingestion event
    alert_info.ticket_id                  = uid                # metadata reference
    alert_info.source_grouping_identifier = uid                # deduplication key
    alert_info.name = display_name
    # Case title in the tenant is seeded from rule_generator, so include the host
    # here so the case list shows the violated URL's host instead of just the
    # generic case type. Playbooks should match by prefix (startswith) or by
    # device_product rather than exact rule_generator equality.
    alert_info.rule_generator = "{}: {}".format(type_prefix, host)
    alert_info.start_time = unix_now()
    alert_info.end_time = unix_now()
    alert_info.priority = severity_map.get(alert_severity, 60)  # default Medium
    alert_info.device_vendor = Config.GC_ALERT_VENDOR
    alert_info.device_product = Config.GC_ALERT_PRODUCT
    alert_info.environment = siemplify.context.connector_info.environment

    event = {
        "StartTime": unix_now(),
        "EndTime": unix_now(),
        "name": display_name,
        "event_type": "DestinationURL",
        "device_product": alert_info.device_product,
        "violation_url": fake_uri,
        "violation_uid": uid,
        "severity": 8
    }
    alert_info.events.append(event)

    return alert_info


def gather_events(siemplify, start_date):
    collection = "violation/list"

    connector = GIBConnector(siemplify)
    creds = (
        extract_connector_param(siemplify, param_name="API login", print_value=False),
        extract_connector_param(siemplify, param_name="API key", print_value=False),
        extract_connector_param(siemplify, param_name="API URL", print_value=False)
    )
    poller = connector.init_action_poller(creds=creds)

    siemplify.LOGGER.info('──── GATHER SEQUPDATE')

    fetched_ts = siemplify.fetch_timestamp(datetime_format=False, timezone=False)
    siemplify.LOGGER.info("fetch_ts: {}".format(fetched_ts))

    if fetched_ts:
        init_seq_update = fetched_ts
    else:
        if not start_date:
            start_date = get_default_date(days=1)

        siemplify.LOGGER.info("Start date: {}".format(start_date))

        _seq_update_dict = poller.get_seq_update_dict(date=start_date, collection_name=collection)
        init_seq_update = _seq_update_dict.get(collection, None)

    siemplify.LOGGER.info("Sequence update number: {}".format(init_seq_update))

    api_url = extract_connector_param(siemplify, param_name="API URL", print_value=False)
    _debug_params = urlencode({"seqUpdate": init_seq_update, "typoSquatting": "true"})
    siemplify.LOGGER.info("DEBUG request: {}?{}".format(urljoin(api_url, collection), _debug_params))

    # use_typo_squatting=True filters for typosquatting domains.
    # ciaops sets sequpdate=1 automatically when sequpdate=None.
    generator = poller.create_update_generator(
        collection_name=collection,
        sequpdate=init_seq_update,
        use_typo_squatting=True
    )

    time.sleep(1)

    siemplify.LOGGER.info('──── PARSE DATA')

    for portion in generator:
        parsed_portion = portion.parse_portion()

        siemplify.LOGGER.info("Fetched {} events".format(len(parsed_portion) if parsed_portion else 0))

        siemplify.save_timestamp(datetime_format=False, timezone=False, new_timestamp=portion.sequpdate)

        return parsed_portion

    return None


if __name__ == "__main__":
    main()
