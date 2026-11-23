from __future__ import annotations

import datetime
import json
import sys
from typing import TYPE_CHECKING, Any

from EnvironmentCommon import GetEnvironmentCommonFactory
from soar_sdk.SiemplifyConnectors import SiemplifyConnectorExecution
from soar_sdk.SiemplifyConnectorsDataModel import AlertInfo
from soar_sdk.SiemplifyUtils import output_handler, unix_now
from TIPCommon.extraction import extract_connector_param
from TIPCommon.smp_time import is_approaching_timeout
from TIPCommon.utils import is_overflowed

from ..core import constants
from ..core.datamodels import (
    Finding,
    Insight,
    parse_timestamp,
    severity_rank,
    severity_to_priority,
    to_iso,
    to_unix_ms,
)
from ..core.huntbase_manager import HuntbaseManager

if TYPE_CHECKING:
    from collections.abc import Callable

# ==============================================================================
# Pulls confirmed Huntbase findings and/or high-severity Huntbase insights into
# Google SecOps SOAR as alerts. Each run reads items created since a watermark
# kept in the connector's context, skips ids it already ingested, and stores the
# new watermark and ids when the run succeeds.
# ==============================================================================

KIND_FINDING = "finding"
KIND_INSIGHT = "insight"

ENTITY_FIELD_BY_TYPE = {
    "ip": "ip",
    "ipv4": "ip",
    "ipv6": "ip",
    "ip_address": "ip",
    "address": "ip",
    "host": "hostname",
    "hostname": "hostname",
    "device": "hostname",
    "endpoint": "hostname",
    "user": "user",
    "username": "user",
    "account": "user",
    "domain": "domain",
    "fqdn": "domain",
    "url": "url",
    "hash": "file_hash",
    "md5": "file_hash",
    "sha1": "file_hash",
    "sha256": "file_hash",
    "file_hash": "file_hash",
}

connector_starting_time = unix_now()


class ConnectorParams:
    """All connector parameters, read once."""

    def __init__(self, siemplify: SiemplifyConnectorExecution) -> None:
        def param(name: str, **kwargs: Any) -> Any:  # noqa: ANN401
            return extract_connector_param(siemplify, param_name=name, **kwargs)

        self.api_root = param(constants.PARAM_API_ROOT, is_mandatory=True, print_value=True)
        self.api_key = param(constants.PARAM_API_KEY, is_mandatory=True, print_value=False)
        self.verify_ssl = param(constants.PARAM_VERIFY_SSL, input_type=bool, default_value=True, print_value=True)
        self.source = param("Source", default_value=constants.SOURCE_FINDINGS, print_value=True)
        self.dispositions = param(
            "Finding Dispositions", default_value=",".join(constants.DEFAULT_FINDING_DISPOSITIONS), print_value=True
        )
        self.min_severity = param(
            "Lowest Insight Severity", default_value=constants.DEFAULT_INSIGHT_MIN_SEVERITY, print_value=True
        )
        self.max_hours_backwards = param(
            "Max Hours Backwards",
            input_type=int,
            default_value=constants.DEFAULT_MAX_HOURS_BACKWARDS,
            print_value=True,
        )
        self.max_alerts = param(
            "Max Alerts Per Cycle",
            input_type=int,
            default_value=constants.DEFAULT_MAX_ALERTS_PER_CYCLE,
            print_value=True,
        )
        self.environment_field = param("Environment Field Name", default_value="", print_value=True)
        self.environment_regex = param("Environment Regex Pattern", default_value=".*", print_value=True)
        self.device_product_field = param("DeviceProductField", default_value="device_product", print_value=True)
        self.timeout = param("PythonProcessTimeout", input_type=int, is_mandatory=True, print_value=True)

    def validate(self) -> None:
        if self.source not in {constants.SOURCE_FINDINGS, constants.SOURCE_INSIGHTS, constants.SOURCE_BOTH}:
            msg = (
                f"Source must be one of: {constants.SOURCE_FINDINGS}, {constants.SOURCE_INSIGHTS}, "
                f"{constants.SOURCE_BOTH}."
            )
            raise ValueError(msg)
        if self.max_alerts < 1:
            msg = "Max Alerts Per Cycle must be at least 1."
            raise ValueError(msg)
        if self.max_hours_backwards < 1:
            msg = "Max Hours Backwards must be at least 1."
            raise ValueError(msg)
        self.min_severity = (self.min_severity or constants.DEFAULT_INSIGHT_MIN_SEVERITY).strip().lower()
        if severity_rank(self.min_severity) < 0:
            msg = f"Lowest Insight Severity must be one of: {', '.join(constants.SEVERITY_ORDER)}."
            raise ValueError(msg)

    @property
    def wants_findings(self) -> bool:
        return self.source in {constants.SOURCE_FINDINGS, constants.SOURCE_BOTH}

    @property
    def wants_insights(self) -> bool:
        return self.source in {constants.SOURCE_INSIGHTS, constants.SOURCE_BOTH}

    @property
    def disposition_list(self) -> list[str]:
        return [d.strip().lower() for d in (self.dispositions or "").split(",") if d.strip()]

    @property
    def insight_severities(self) -> list[str]:
        floor = severity_rank(self.min_severity)
        return [s for s in constants.SEVERITY_ORDER if severity_rank(s) >= floor]


# ------------------------------------------------------------------ context


def _context_identifier(siemplify: SiemplifyConnectorExecution) -> str:
    return siemplify.context.connector_info.identifier


def read_json_context(siemplify: SiemplifyConnectorExecution, key: str, default: Any) -> Any:  # noqa: ANN401
    raw = siemplify.get_connector_context_property(_context_identifier(siemplify), key)
    if not raw:
        return default
    try:
        return json.loads(raw)
    except (TypeError, ValueError):
        siemplify.LOGGER.error(f"Ignoring unreadable connector context '{key}'")
        return default


def write_json_context(siemplify: SiemplifyConnectorExecution, key: str, value: Any) -> None:  # noqa: ANN401
    siemplify.set_connector_context_property(_context_identifier(siemplify), key, json.dumps(value))


def initial_watermark(watermarks: dict[str, str], kind: str, max_hours_backwards: int, overlap_minutes: int = 0) -> str:
    """Where to read from: the saved watermark (minus an overlap), never older than the floor."""
    floor = datetime.datetime.now(tz=datetime.UTC) - datetime.timedelta(hours=max_hours_backwards)
    saved = parse_timestamp(watermarks.get(kind))
    if saved:
        saved -= datetime.timedelta(minutes=overlap_minutes)
    return to_iso(max(saved, floor) if saved else floor)


# ---------------------------------------------------------------- fetching


def fetch_new(
    fetch_page: Callable[[int], list[Any]],
    item_id: Callable[[Any], str],
    processed: set[str],
    limit: int,
    timeout: int,
) -> list[Any]:
    """Page through a source until `limit` unseen items are collected or pages run out."""
    collected: list[Any] = []
    offset = 0
    while len(collected) < limit:
        if is_approaching_timeout(connector_starting_time, timeout):
            break
        page = fetch_page(offset)
        for item in page:
            if item_id(item) and item_id(item) not in processed and len(collected) < limit:
                collected.append(item)
        if len(page) < constants.CONNECTOR_PAGE_SIZE:
            break
        offset += len(page)
    return collected


# ------------------------------------------------------------------ mapping


def _flat(values: dict[str, Any]) -> dict[str, str]:
    return {key: str(value) for key, value in values.items() if value not in (None, "", [], {})}


def entity_events(entities: list[dict[str, Any]], base: dict[str, Any]) -> list[dict[str, str]]:
    events = []
    for entity in entities:
        field = ENTITY_FIELD_BY_TYPE.get(str(entity.get("type") or "").lower())
        value = entity.get("value")
        if not field or not value:
            continue
        event = dict(base)
        event["event_type"] = f"{base['event_type']} Entity"
        event[field] = value
        event["entity_role"] = entity.get("role")
        events.append(_flat(event))
    return events


def build_alert(
    item: Finding | Insight,
    kind: str,
    environment_common: Any,  # noqa: ANN401
    device_product_field: str,
) -> AlertInfo:
    now_ms = unix_now()
    if kind == KIND_FINDING:
        created_ms = to_unix_ms(item.created_at) or now_ms
        base = {
            "event_type": "Huntbase Finding",
            "device_product": constants.DEVICE_PRODUCT,
            "device_vendor": constants.DEVICE_VENDOR,
            "id": item.finding_id,
            "title": item.title,
            "summary": item.summary,
            "severity": item.severity,
            "disposition": item.disposition,
            "hunt_id": item.hunt_id,
            "hunt_title": item.hunt_title,
            "url": item.url,
            "start_time": created_ms,
            "end_time": to_unix_ms(item.updated_at) or created_ms,
        }
        entities = item.entities
        rule_generator = constants.RULE_GENERATOR_FINDING
        alert_id = item.finding_id
        name = item.title
        severity = item.severity
    else:
        created_ms = to_unix_ms(item.time) or to_unix_ms(item.created_at) or now_ms
        base = {
            "event_type": "Huntbase Insight",
            "device_product": constants.DEVICE_PRODUCT,
            "device_vendor": constants.DEVICE_VENDOR,
            "id": item.insight_id,
            "title": item.title,
            "severity": item.severity,
            "status": item.status,
            "source_product": item.source_product,
            "watcher_name": item.watcher_name,
            "url": item.url,
            "start_time": created_ms,
            "end_time": created_ms,
        }
        entities = item.entities()
        rule_generator = item.watcher_name or constants.RULE_GENERATOR_INSIGHT
        alert_id = item.insight_id
        name = item.title
        severity = item.severity

    events = [_flat(base), *entity_events(entities, base)]

    alert_info = AlertInfo()
    alert_info.ticket_id = alert_id
    alert_info.display_id = f"HB-{kind}-{alert_id}"
    alert_info.name = name
    alert_info.description = base.get("summary") or name
    alert_info.reason = base.get("disposition") or base.get("status") or kind
    alert_info.rule_generator = rule_generator
    alert_info.device_vendor = constants.DEVICE_VENDOR
    alert_info.device_product = base.get(device_product_field) or constants.DEVICE_PRODUCT
    alert_info.priority = severity_to_priority(severity)
    alert_info.start_time = base["start_time"]
    alert_info.end_time = base["end_time"]
    alert_info.environment = environment_common.get_environment(base)
    alert_info.events = events
    alert_info.extensions = _flat({"huntbase_url": item.url, "huntbase_kind": kind})
    return alert_info


def item_time(item: Finding | Insight) -> datetime.datetime | None:
    if isinstance(item, Finding):
        return parse_timestamp(item.created_at)
    return parse_timestamp(item.time) or parse_timestamp(item.created_at)


# --------------------------------------------------------------------- main


@output_handler
def main(is_test_run: bool) -> None:
    siemplify = SiemplifyConnectorExecution()
    siemplify.script_name = constants.FINDINGS_CONNECTOR_SCRIPT_NAME
    if is_test_run:
        siemplify.LOGGER.info('***** This is an "IDE Play Button Run Connector once" test run ******')

    siemplify.LOGGER.info("==================== Main - Param Init ====================")
    alerts: list[AlertInfo] = []
    try:
        params = ConnectorParams(siemplify)
        params.validate()
        limit = constants.CONNECTOR_TEST_RUN_MAX_ALERTS if is_test_run else params.max_alerts

        siemplify.LOGGER.info("------------------- Main - Started -------------------")
        manager = HuntbaseManager(params.api_root, params.api_key, params.verify_ssl, logger=siemplify.LOGGER)
        watermarks: dict[str, str] = read_json_context(siemplify, constants.WATERMARK_KEY, {})
        processed_ids: list[str] = read_json_context(siemplify, constants.PROCESSED_IDS_KEY, [])
        processed = set(processed_ids)

        candidates: list[tuple[str, Finding | Insight]] = []
        if params.wants_findings:
            since = initial_watermark(watermarks, KIND_FINDING, params.max_hours_backwards)
            siemplify.LOGGER.info(f"Fetching Huntbase findings since {since}")
            findings = fetch_new(
                lambda offset: manager.list_findings(since, params.disposition_list, offset=offset),
                lambda f: f"{KIND_FINDING}:{f.finding_id}",
                processed,
                limit,
                params.timeout,
            )
            candidates += [(KIND_FINDING, f) for f in findings]
        if params.wants_insights:
            # /insights filters on event time, so re-read an overlap and rely on id dedupe
            since = initial_watermark(
                watermarks, KIND_INSIGHT, params.max_hours_backwards, constants.INSIGHT_OVERLAP_MINUTES
            )
            for severity in params.insight_severities:
                siemplify.LOGGER.info(f"Fetching Huntbase {severity} insights since {since}")
                insights = fetch_new(
                    lambda offset, sev=severity: manager.list_insights(since, sev, offset=offset),
                    lambda i: f"{KIND_INSIGHT}:{i.insight_id}",
                    processed,
                    limit,
                    params.timeout,
                )
                candidates += [(KIND_INSIGHT, i) for i in insights]

        epoch = datetime.datetime.min.replace(tzinfo=datetime.UTC)
        candidates.sort(key=lambda pair: item_time(pair[1]) or epoch)
        siemplify.LOGGER.info(f"Found {len(candidates)} new Huntbase item(s)")

        environment_common = GetEnvironmentCommonFactory.create_environment_manager(
            siemplify, params.environment_field, params.environment_regex
        )
        new_watermarks = dict(watermarks)
        for kind, item in candidates:
            if len(alerts) >= limit:
                siemplify.LOGGER.info(f"Reached the limit of {limit} alerts for this cycle")
                break
            if is_approaching_timeout(connector_starting_time, params.timeout):
                siemplify.LOGGER.info("Timeout is approaching. Connector will gracefully exit")
                break
            key = f"{kind}:{item.finding_id if kind == KIND_FINDING else item.insight_id}"
            try:
                alert_info = build_alert(item, kind, environment_common, params.device_product_field)
            except Exception as error:  # noqa: BLE001
                siemplify.LOGGER.error(f"Failed to build an alert from Huntbase {key}: {error}")
                siemplify.LOGGER.exception(error)
                if is_test_run:
                    raise
                continue

            processed_ids.append(key)
            stamp = item_time(item)
            current = parse_timestamp(new_watermarks.get(kind))
            if stamp and (current is None or stamp > current):
                new_watermarks[kind] = to_iso(stamp)

            if is_overflowed(siemplify, alert_info, is_test_run):
                siemplify.LOGGER.info(
                    f"{alert_info.rule_generator}-{alert_info.ticket_id}-{alert_info.environment}-"
                    f"{alert_info.device_product} found as overflow alert. Skipping."
                )
                continue
            alerts.append(alert_info)
            siemplify.LOGGER.info(f"Added alert {alert_info.display_id} to package results")

        if not is_test_run:
            write_json_context(siemplify, constants.PROCESSED_IDS_KEY, processed_ids[-constants.MAX_STORED_IDS :])
            write_json_context(siemplify, constants.WATERMARK_KEY, new_watermarks)

        siemplify.LOGGER.info(f"Created total of {len(alerts)} alerts")
    except Exception as error:
        siemplify.LOGGER.error(f"Got exception on main handler. Error: {error}")
        siemplify.LOGGER.exception(error)
        if is_test_run:
            raise

    siemplify.LOGGER.info("------------------- Main - Finished -------------------")
    siemplify.return_package(alerts)


if __name__ == "__main__":
    # Connectors are run in iterations. The interval is configurable from the ConnectorsScreen UI.
    is_test_run = not (len(sys.argv) < 2 or sys.argv[1] == "True")
    main(is_test_run)
