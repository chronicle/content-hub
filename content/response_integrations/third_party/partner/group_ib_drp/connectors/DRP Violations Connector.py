from __future__ import annotations
import uuid
from datetime import datetime, timedelta, timezone
from urllib.parse import urljoin, urlencode

from soar_sdk.SiemplifyConnectors import SiemplifyConnectorExecution
from soar_sdk.SiemplifyConnectorsDataModel import AlertInfo
from soar_sdk.SiemplifyUtils import output_handler, unix_now

from TIPCommon.extraction import extract_connector_param

# Import Managers
from ..core.config import Config
from ..core.UtilsManager import GIBConnector, extract_host


_SEVERITY_MAP = {"Informative": -1, "Low": 40, "Medium": 60, "High": 80, "Critical": 100}
_DEFAULT_PRIORITY = 60
_EVENT_SEVERITY = 8  # DRP violation severity used by the inner event payload


def get_default_date(days=1):
    return (datetime.now(tz=timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")


@output_handler
def main() -> None:
    """Run the DRP Violations connector ingestion cycle.

    Reads the connector's script parameters (case name/type/severity, start
    date, optional brand IDs, approve states, subtypes, sections), pulls a
    single portion of violation events from the Group-IB DRP API via
    ``gather_events``, builds one ``AlertInfo`` per event with a
    deterministic ``source_grouping_identifier`` so SOAR can deduplicate,
    and pushes the resulting batch back through
    ``siemplify.return_package``. One portion per scheduled run keeps
    memory and runtime bounded; the persisted ``sequpdate`` cursor lets
    the next run pick up where this one left off. The cursor is persisted
    via ``siemplify.save_timestamp`` only after ``return_package`` returns
    without raising; on any failure the cursor stays put so the next run
    retries the same portion and SOAR's grouping-identifier dedupe keeps
    things consistent.
    """
    siemplify = SiemplifyConnectorExecution()

    # Google SecOps base class set up
    siemplify.script_name = Config.GC_CONNECTOR_SCRIPT_NAME

    # Get basic alert configuration
    alert_name = extract_connector_param(siemplify, param_name="Case name", print_value=True)
    alert_type = extract_connector_param(siemplify, param_name="Case type", print_value=True)
    alert_severity = extract_connector_param(siemplify, param_name="Case severity", print_value=True)
    start_date = extract_connector_param(siemplify, param_name="Start date", print_value=True)

    # Optional filters
    brand_ids_raw = extract_connector_param(siemplify, param_name="Brand IDs", print_value=True)
    approve_states_raw = extract_connector_param(siemplify, param_name="Approve States", print_value=True)
    subtypes_raw = extract_connector_param(siemplify, param_name="Subtypes", print_value=True)
    section_raw = extract_connector_param(siemplify, param_name="Section", print_value=True)

    brand_ids = [b.strip() for b in brand_ids_raw.split(",") if b.strip()] if brand_ids_raw else None
    approve_states = [int(s.strip()) for s in approve_states_raw.split(",") if s.strip()] if approve_states_raw else None
    subtypes = [int(s.strip()) for s in subtypes_raw.split(",") if s.strip()] if subtypes_raw else None
    section = int(section_raw.strip()) if section_raw and section_raw.strip() else None

    # Create alerts holder (The main output of each connector run)
    alerts = []
    events, state = gather_events(
        siemplify, start_date,
        brand_ids=brand_ids,
        approve_states=approve_states,
        subtypes=subtypes,
        section=section,
    )

    try:
        for _event in events:
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
                alert_severity=alert_severity,
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
                fake_uri,
            ))
            alerts.append(alert_instance)

        siemplify.LOGGER.info("Returning {} alert(s) to package".format(len(alerts)))
        siemplify.return_package(alerts)

        if state["last_sequpdate"] != state["init_sequpdate"]:
            siemplify.save_timestamp(
                datetime_format=False, timezone=False,
                new_timestamp=state["last_sequpdate"],
            )
            siemplify.LOGGER.info("Persisted cursor sequpdate={}".format(state["last_sequpdate"]))
        else:
            siemplify.LOGGER.info("Cursor unchanged; not persisting.")

    except Exception as e:
        siemplify.LOGGER.error(
            "Failed to process violations after {} alert(s); cursor NOT advanced — next run will retry from sequpdate {} (SOAR dedupes via source_grouping_identifier).".format(
                len(alerts), state["init_sequpdate"],
            )
        )
        siemplify.LOGGER.exception(e)


def create_alert(siemplify, uid, fake_uri, alert_name, alert_type, alert_severity):
    """Creates one AlertInfo per violation."""

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
    alert_info.priority = _SEVERITY_MAP.get(alert_severity, _DEFAULT_PRIORITY)
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
        "severity": _EVENT_SEVERITY,
    }
    alert_info.events.append(event)

    return alert_info


def gather_events(siemplify, start_date, brand_ids=None, approve_states=None, subtypes=None, section=None):
    """Pull a single portion of violation events from the DRP API.

    Returns a tuple ``(events, state)`` where ``events`` is the list of
    parsed violation events from the first portion (possibly empty) and
    ``state`` is a dict carrying the cursor info. Polling one portion per
    scheduled run is intentional: it bounds memory and runtime, and the
    persisted ``sequpdate`` cursor lets the next run pick up where this
    one left off. ``save_timestamp`` is intentionally NOT called here —
    the cursor must only be persisted after ``return_package`` succeeds
    in ``main()`` so a crash leaves the cursor unchanged and SOAR's
    ``source_grouping_identifier`` dedupe handles the retry.
    """
    collection = "violation/list"

    connector = GIBConnector(siemplify)
    api_url = extract_connector_param(siemplify, param_name="API URL", print_value=False)
    creds = (
        extract_connector_param(siemplify, param_name="API login", print_value=False),
        extract_connector_param(siemplify, param_name="API key", print_value=False),
        api_url,
        extract_connector_param(siemplify, param_name="Verify SSL", input_type=bool,
                                default_value=True, print_value=True),
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
    siemplify.LOGGER.info("DEBUG request: {}?{}".format(
        urljoin(api_url, collection), urlencode({"seqUpdate": init_seq_update}),
    ))

    generator = poller.create_update_generator(
        collection_name=collection,
        sequpdate=init_seq_update,
        brands=brand_ids,
        approve_states=approve_states,
        subtypes=subtypes,
        section=section,
    )

    siemplify.LOGGER.info('──── PARSE DATA')

    state = {
        "init_sequpdate": init_seq_update,
        "last_sequpdate": init_seq_update,
    }

    portion = next(generator, None)
    if portion is None:
        siemplify.LOGGER.info("No portions available from DRP API.")
        return [], state

    parsed_portion = portion.parse_portion() or []
    state["last_sequpdate"] = portion.sequpdate
    siemplify.LOGGER.info("Fetched {} events (sequpdate={})".format(
        len(parsed_portion), portion.sequpdate,
    ))
    return parsed_portion, state


if __name__ == "__main__":
    main()
