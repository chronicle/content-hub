"""Pulls confirmed Huntbase findings and/or high-severity Huntbase insights into Google SecOps SOAR as alerts.

Each run reads items created since a watermark kept in the connector's context, skips ids it already
ingested, and stores the new watermark and ids when the run succeeds.
"""

from __future__ import annotations

import dataclasses
import datetime
import json
import sys
from typing import TYPE_CHECKING, TypeVar

from soar_sdk.SiemplifyConnectors import SiemplifyConnectorExecution
from soar_sdk.SiemplifyConnectorsDataModel import AlertInfo
from soar_sdk.SiemplifyUtils import output_handler, unix_now
from TIPCommon.envcommon import GetEnvironmentCommonFactory
from TIPCommon.extraction import extract_connector_param
from TIPCommon.smp_time import is_approaching_timeout
from TIPCommon.utils import is_overflowed

from ..core import constants
from ..core.datamodels import (
    Finding,
    FindingsQuery,
    HuntbaseConfig,
    Insight,
    InsightsQuery,
    parse_timestamp,
    severity_rank,
    severity_to_priority,
    to_iso,
    to_unix_ms,
)
from ..core.huntbase_manager import HuntbaseManager

if TYPE_CHECKING:
    from collections.abc import Callable

    from TIPCommon.envcommon import EnvironmentHandle
    from TIPCommon.types import SingleJson

_T = TypeVar("_T")
_Q = TypeVar("_Q", FindingsQuery, InsightsQuery)

KIND_FINDING: str = "finding"
KIND_INSIGHT: str = "insight"

ENTITY_FIELD_BY_TYPE: dict[str, str] = {
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

connector_starting_time: int = unix_now()


class ConnectorParams:
    """All connector parameters, read once."""

    def __init__(self, siemplify: SiemplifyConnectorExecution) -> None:
        self.api_root: str = extract_connector_param(
            siemplify,
            param_name=constants.PARAM_API_ROOT,
            is_mandatory=True,
            print_value=True,
        )
        self.api_key: str = extract_connector_param(
            siemplify,
            param_name=constants.PARAM_API_KEY,
            is_mandatory=True,
            print_value=False,
        )
        self.verify_ssl: bool = extract_connector_param(
            siemplify,
            param_name=constants.PARAM_VERIFY_SSL,
            input_type=bool,
            default_value=True,
            print_value=True,
        )
        self.source: str = extract_connector_param(
            siemplify,
            param_name="Source",
            default_value=constants.SOURCE_FINDINGS,
            print_value=True,
        )
        self.dispositions: str = extract_connector_param(
            siemplify,
            param_name="Finding Dispositions",
            default_value=",".join(constants.DEFAULT_FINDING_DISPOSITIONS),
            print_value=True,
        )
        self.min_severity: str = extract_connector_param(
            siemplify,
            param_name="Lowest Insight Severity",
            default_value=constants.DEFAULT_INSIGHT_MIN_SEVERITY,
            print_value=True,
        )
        self.max_hours_backwards: int = extract_connector_param(
            siemplify,
            param_name="Max Hours Backwards",
            input_type=int,
            default_value=constants.DEFAULT_MAX_HOURS_BACKWARDS,
            print_value=True,
        )
        self.max_alerts: int = extract_connector_param(
            siemplify,
            param_name="Max Alerts Per Cycle",
            input_type=int,
            default_value=constants.DEFAULT_MAX_ALERTS_PER_CYCLE,
            print_value=True,
        )
        self.environment_field: str = extract_connector_param(
            siemplify,
            param_name="Environment Field Name",
            default_value="",
            print_value=True,
        )
        self.environment_regex: str = extract_connector_param(
            siemplify,
            param_name="Environment Regex Pattern",
            default_value=".*",
            print_value=True,
        )
        self.device_product_field: str = extract_connector_param(
            siemplify,
            param_name="DeviceProductField",
            default_value="device_product",
            print_value=True,
        )
        self.timeout: int = extract_connector_param(
            siemplify,
            param_name="PythonProcessTimeout",
            input_type=int,
            is_mandatory=True,
            print_value=True,
        )

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
    def config(self) -> HuntbaseConfig:
        return HuntbaseConfig(api_root=self.api_root, api_key=self.api_key, verify_ssl=self.verify_ssl)

    @property
    def wants_findings(self) -> bool:
        return self.source in {constants.SOURCE_FINDINGS, constants.SOURCE_BOTH}

    @property
    def wants_insights(self) -> bool:
        return self.source in {constants.SOURCE_INSIGHTS, constants.SOURCE_BOTH}

    @property
    def disposition_list(self) -> tuple[str, ...]:
        return tuple(d.strip().lower() for d in (self.dispositions or "").split(",") if d.strip())

    @property
    def insight_severities(self) -> list[str]:
        floor = severity_rank(self.min_severity)
        return [s for s in constants.SEVERITY_ORDER if severity_rank(s) >= floor]


@dataclasses.dataclass(slots=True, frozen=True)
class FetchBudget:
    """How many unseen items one source may return this cycle, and when to stop paging."""

    processed: set[str]
    limit: int
    timeout: int


@dataclasses.dataclass(slots=True, frozen=True)
class AlertContext:
    """What every alert of a cycle is built with."""

    environment_common: EnvironmentHandle
    device_product_field: str


@dataclasses.dataclass(slots=True, frozen=True)
class CycleState:
    """One connector run: its parameters, saved context and the alerts it collects."""

    params: ConnectorParams
    limit: int
    is_test_run: bool
    watermarks: dict[str, str]
    processed_ids: list[str]
    alerts: list[AlertInfo]

    @property
    def budget(self) -> FetchBudget:
        return FetchBudget(processed=set(self.processed_ids), limit=self.limit, timeout=self.params.timeout)


@dataclasses.dataclass(slots=True, frozen=True)
class _AlertSource:
    """The parts of an alert that depend on the item kind."""

    kind: str
    alert_id: str
    rule_generator: str
    base_event: SingleJson
    entities: list[SingleJson]


def _context_identifier(siemplify: SiemplifyConnectorExecution) -> str:
    return siemplify.context.connector_info.identifier


def read_json_context(siemplify: SiemplifyConnectorExecution, key: str, default: _T) -> _T:
    raw: str | None = siemplify.get_connector_context_property(_context_identifier(siemplify), key)
    if not raw:
        return default
    try:
        return json.loads(raw)
    except (TypeError, ValueError):
        siemplify.LOGGER.error(f"Ignoring unreadable connector context '{key}'")
        return default


def write_json_context(siemplify: SiemplifyConnectorExecution, key: str, value: object) -> None:
    siemplify.set_connector_context_property(_context_identifier(siemplify), key, json.dumps(value))


def initial_watermark(saved_watermark: str | None, max_hours_backwards: int, overlap_minutes: int = 0) -> str:
    """Where to read from: the saved watermark (minus an overlap), never older than the floor."""
    floor = datetime.datetime.now(tz=datetime.UTC) - datetime.timedelta(hours=max_hours_backwards)
    saved = parse_timestamp(saved_watermark)
    if saved:
        saved -= datetime.timedelta(minutes=overlap_minutes)
    return to_iso(max(saved, floor) if saved else floor)


def fetch_new(fetch_page: Callable[[int], list[_T]], item_id: Callable[[_T], str], budget: FetchBudget) -> list[_T]:
    """Page through a source until `budget.limit` unseen items are collected or pages run out."""
    collected: list[_T] = []
    offset = 0
    while len(collected) < budget.limit:
        if is_approaching_timeout(connector_starting_time, budget.timeout):
            break
        page = fetch_page(offset)
        for item in page:
            if item_id(item) and item_id(item) not in budget.processed and len(collected) < budget.limit:
                collected.append(item)
        if len(page) < constants.CONNECTOR_PAGE_SIZE:
            break
        offset += len(page)
    return collected


def _pager(fetch: Callable[[_Q], list[_T]], query: _Q) -> Callable[[int], list[_T]]:
    """Turn a query-taking list call into a fetch_page(offset) function."""
    return lambda offset: fetch(dataclasses.replace(query, offset=offset))


def item_key(item: Finding | Insight) -> str:
    if isinstance(item, Finding):
        return f"{KIND_FINDING}:{item.finding_id}"
    return f"{KIND_INSIGHT}:{item.insight_id}"


def _flat(values: SingleJson) -> dict[str, str]:
    return {key: str(value) for key, value in values.items() if value not in (None, "", [], {})}


def entity_events(entities: list[SingleJson], base: SingleJson) -> list[dict[str, str]]:
    events: list[dict[str, str]] = []
    for entity in entities:
        field = ENTITY_FIELD_BY_TYPE.get(str(entity.get("type") or "").lower())
        value = entity.get("value")
        if not field or not value:
            continue
        event: SingleJson = dict(base)
        event["event_type"] = f"{base['event_type']} Entity"
        event[field] = value
        event["entity_role"] = entity.get("role")
        events.append(_flat(event))
    return events


def _finding_source(finding: Finding, now_ms: int) -> _AlertSource:
    created_ms = to_unix_ms(finding.created_at) or now_ms
    base: SingleJson = {
        "event_type": "Huntbase Finding",
        "device_product": constants.DEVICE_PRODUCT,
        "device_vendor": constants.DEVICE_VENDOR,
        "id": finding.finding_id,
        "title": finding.title,
        "summary": finding.summary,
        "severity": finding.severity,
        "disposition": finding.disposition,
        "hunt_id": finding.hunt_id,
        "hunt_title": finding.hunt_title,
        "url": finding.url,
        "start_time": created_ms,
        "end_time": to_unix_ms(finding.updated_at) or created_ms,
    }
    return _AlertSource(
        kind=KIND_FINDING,
        alert_id=finding.finding_id,
        rule_generator=constants.RULE_GENERATOR_FINDING,
        base_event=base,
        entities=finding.entities,
    )


def _insight_source(insight: Insight, now_ms: int) -> _AlertSource:
    created_ms = to_unix_ms(insight.time) or to_unix_ms(insight.created_at) or now_ms
    base: SingleJson = {
        "event_type": "Huntbase Insight",
        "device_product": constants.DEVICE_PRODUCT,
        "device_vendor": constants.DEVICE_VENDOR,
        "id": insight.insight_id,
        "title": insight.title,
        "severity": insight.severity,
        "status": insight.status,
        "source_product": insight.source_product,
        "watcher_name": insight.watcher_name,
        "url": insight.url,
        "start_time": created_ms,
        "end_time": created_ms,
    }
    return _AlertSource(
        kind=KIND_INSIGHT,
        alert_id=insight.insight_id,
        rule_generator=insight.watcher_name or constants.RULE_GENERATOR_INSIGHT,
        base_event=base,
        entities=insight.entities(),
    )


def build_alert(item: Finding | Insight, context: AlertContext) -> AlertInfo:
    now_ms = unix_now()
    source = _finding_source(item, now_ms) if isinstance(item, Finding) else _insight_source(item, now_ms)
    base = source.base_event

    alert_info = AlertInfo()
    alert_info.ticket_id = source.alert_id
    alert_info.display_id = f"HB-{source.kind}-{source.alert_id}"
    alert_info.name = item.title
    alert_info.description = base.get("summary") or item.title
    alert_info.reason = base.get("disposition") or base.get("status") or source.kind
    alert_info.rule_generator = source.rule_generator
    alert_info.device_vendor = constants.DEVICE_VENDOR
    alert_info.device_product = base.get(context.device_product_field) or constants.DEVICE_PRODUCT
    alert_info.priority = severity_to_priority(item.severity)
    alert_info.start_time = base["start_time"]
    alert_info.end_time = base["end_time"]
    alert_info.environment = context.environment_common.get_environment(base)
    alert_info.events = [_flat(base), *entity_events(source.entities, base)]
    alert_info.extensions = _flat({"huntbase_url": item.url, "huntbase_kind": source.kind})
    return alert_info


def item_time(item: Finding | Insight) -> datetime.datetime | None:
    if isinstance(item, Finding):
        return parse_timestamp(item.created_at)
    return parse_timestamp(item.time) or parse_timestamp(item.created_at)


def _fetch_candidates(
    siemplify: SiemplifyConnectorExecution,
    manager: HuntbaseManager,
    cycle: CycleState,
) -> list[Finding | Insight]:
    params = cycle.params
    budget = cycle.budget
    candidates: list[Finding | Insight] = []
    if params.wants_findings:
        since = initial_watermark(cycle.watermarks.get(KIND_FINDING), params.max_hours_backwards)
        siemplify.LOGGER.info(f"Fetching Huntbase findings since {since}")
        query = FindingsQuery(since=since, dispositions=params.disposition_list)
        candidates += fetch_new(_pager(manager.list_findings, query), item_key, budget)
    if params.wants_insights:
        # /insights filters on event time, so re-read an overlap and rely on id dedupe
        since = initial_watermark(
            cycle.watermarks.get(KIND_INSIGHT),
            params.max_hours_backwards,
            constants.INSIGHT_OVERLAP_MINUTES,
        )
        for severity in params.insight_severities:
            siemplify.LOGGER.info(f"Fetching Huntbase {severity} insights since {since}")
            query = InsightsQuery(since=since, severity=severity)
            candidates += fetch_new(_pager(manager.list_insights, query), item_key, budget)

    epoch = datetime.datetime.min.replace(tzinfo=datetime.UTC)
    candidates.sort(key=lambda item: item_time(item) or epoch)
    siemplify.LOGGER.info(f"Found {len(candidates)} new Huntbase item(s)")
    return candidates


def _process_candidates(
    siemplify: SiemplifyConnectorExecution,
    candidates: list[Finding | Insight],
    cycle: CycleState,
) -> dict[str, str]:
    """Turn candidates into alerts in `cycle.alerts`; return the advanced watermarks."""
    context = AlertContext(
        environment_common=GetEnvironmentCommonFactory.create_environment_manager(
            siemplify,
            cycle.params.environment_field,
            cycle.params.environment_regex,
        ),
        device_product_field=cycle.params.device_product_field,
    )
    new_watermarks = dict(cycle.watermarks)
    for item in candidates:
        if len(cycle.alerts) >= cycle.limit:
            siemplify.LOGGER.info(f"Reached the limit of {cycle.limit} alerts for this cycle")
            break
        if is_approaching_timeout(connector_starting_time, cycle.params.timeout):
            siemplify.LOGGER.info("Timeout is approaching. Connector will gracefully exit")
            break
        key = item_key(item)
        try:
            alert_info = build_alert(item, context)
        except Exception as error:  # noqa: BLE001
            siemplify.LOGGER.exception(f"Failed to build an alert from Huntbase {key}: {error}")
            if cycle.is_test_run:
                raise
            continue

        cycle.processed_ids.append(key)
        kind = KIND_FINDING if isinstance(item, Finding) else KIND_INSIGHT
        stamp = item_time(item)
        current = parse_timestamp(new_watermarks.get(kind))
        if stamp and (current is None or stamp > current):
            new_watermarks[kind] = to_iso(stamp)

        if is_overflowed(siemplify, alert_info, cycle.is_test_run):
            siemplify.LOGGER.info(
                f"{alert_info.rule_generator}-{alert_info.ticket_id}-{alert_info.environment}-"
                f"{alert_info.device_product} found as overflow alert. Skipping."
            )
            continue
        cycle.alerts.append(alert_info)
        siemplify.LOGGER.info(f"Added alert {alert_info.display_id} to package results")
    return new_watermarks


def _run_cycle(siemplify: SiemplifyConnectorExecution, is_test_run: bool, alerts: list[AlertInfo]) -> None:
    params = ConnectorParams(siemplify)
    params.validate()

    siemplify.LOGGER.info("------------------- Main - Started -------------------")
    cycle = CycleState(
        params=params,
        limit=constants.CONNECTOR_TEST_RUN_MAX_ALERTS if is_test_run else params.max_alerts,
        is_test_run=is_test_run,
        watermarks=read_json_context(siemplify, constants.WATERMARK_KEY, {}),
        processed_ids=read_json_context(siemplify, constants.PROCESSED_IDS_KEY, []),
        alerts=alerts,
    )
    with HuntbaseManager(params.config, logger=siemplify.LOGGER) as manager:
        candidates = _fetch_candidates(siemplify, manager, cycle)
    new_watermarks = _process_candidates(siemplify, candidates, cycle)

    if not is_test_run:
        write_json_context(siemplify, constants.PROCESSED_IDS_KEY, cycle.processed_ids[-constants.MAX_STORED_IDS :])
        write_json_context(siemplify, constants.WATERMARK_KEY, new_watermarks)
    siemplify.LOGGER.info(f"Created total of {len(alerts)} alerts")


@output_handler
def main(is_test_run: bool) -> None:
    siemplify = SiemplifyConnectorExecution()
    siemplify.script_name = constants.FINDINGS_CONNECTOR_SCRIPT_NAME
    if is_test_run:
        siemplify.LOGGER.info('***** This is an "IDE Play Button Run Connector once" test run ******')

    siemplify.LOGGER.info("==================== Main - Param Init ====================")
    alerts: list[AlertInfo] = []
    try:
        _run_cycle(siemplify, is_test_run, alerts)
    except Exception as error:
        siemplify.LOGGER.exception(f"Got exception on main handler. Error: {error}")
        if is_test_run:
            raise

    siemplify.LOGGER.info("------------------- Main - Finished -------------------")
    siemplify.return_package(alerts)


if __name__ == "__main__":
    # Connectors are run in iterations. The interval is configurable from the ConnectorsScreen UI.
    is_test_run = not (len(sys.argv) < 2 or sys.argv[1] == "True")
    main(is_test_run)
