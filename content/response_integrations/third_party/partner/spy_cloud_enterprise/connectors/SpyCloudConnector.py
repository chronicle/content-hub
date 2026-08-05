from __future__ import annotations

import json
import sys
from collections import Counter
from typing import Any, Callable

from EnvironmentCommon import GetEnvironmentCommonFactory
from soar_sdk.SiemplifyConnectors import SiemplifyConnectorExecution
from soar_sdk.SiemplifyUtils import output_handler
from TIPCommon.extraction import extract_connector_param

from ..core.Parser import build_alert_from_udm_event
from ..core.spycloud_udm_converter import SpyCloudUdmConverter
from ..core.SpyCloudManager import SpyCloudManager

CONNECTOR_NAME = "SpyCloud Enterprise Connector"


def _safe_get(dct: Any, *keys: Any, default: Any = None) -> Any:
    current = dct
    for key in keys:
        if not isinstance(current, dict):
            return default
        current = current.get(key)
        if current is None:
            return default
    return current


COLLECTION_SOURCE_FIELD = "spycloud_collection_source"


def _normalize_collection_sources(value: Any) -> list[str]:
    if value in (None, "", [], {}):
        return ["unknown"]

    if isinstance(value, list):
        sources = []
        for item in value:
            sources.extend(_normalize_collection_sources(item))
        return [source for source in dict.fromkeys(sources) if source]

    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return ["unknown"]

        if stripped.startswith("["):
            try:
                parsed = json.loads(stripped)
                if isinstance(parsed, list):
                    return _normalize_collection_sources(parsed)
            except Exception:
                pass

        if "," in stripped:
            parts = [part.strip() for part in stripped.split(",") if part.strip()]
            if parts:
                return [source for source in dict.fromkeys(parts) if source]

        return [stripped]

    return [str(value)]


def _collection_source_label(value: Any) -> str:
    sources = _normalize_collection_sources(value)
    if not sources:
        return "unknown"
    return "+".join(sources)


def _format_source_counts(counter: Counter) -> str:
    if not counter:
        return "none"
    return ", ".join(
        f"{source}={count}" for source, count in sorted(counter.items())
    )


def _count_sources(
    items: Any,
    source_getter: Callable[[Any], list[str]],
) -> Counter:
    counter = Counter()
    for item in items or []:
        for source in source_getter(item):
            counter[source] += 1
    return counter


def _get_raw_record_sources(record: Any) -> list[str]:
    if not isinstance(record, dict):
        return ["unknown"]
    return [_collection_source_label(record.get(COLLECTION_SOURCE_FIELD))]


def _get_udm_event_sources(udm_event: Any) -> list[str]:
    extensions = udm_event.get("extensions", {}) if isinstance(udm_event, dict) else {}
    additional = udm_event.get("additional", {}) if isinstance(udm_event, dict) else {}
    if not isinstance(extensions, dict):
        extensions = {}
    if not isinstance(additional, dict):
        additional = {}
    return [
        _collection_source_label(
            extensions.get(COLLECTION_SOURCE_FIELD) or additional.get(COLLECTION_SOURCE_FIELD)
        )
    ]


def _get_alert_sources(alert: Any) -> list[str]:
    counter = Counter()
    for event in getattr(alert, "events", []) or []:
        if isinstance(event, dict):
            counter[_collection_source_label(event.get(COLLECTION_SOURCE_FIELD))] += 1
    return list(counter.keys()) or ["unknown"]


def _safe_udm_sample(udm_event: Any) -> dict[str, Any]:
    metadata = udm_event.get("metadata", {}) if isinstance(udm_event, dict) else {}
    security_result = udm_event.get("security_result", {}) if isinstance(udm_event, dict) else {}
    extensions = udm_event.get("extensions", {}) if isinstance(udm_event, dict) else {}
    additional = udm_event.get("additional", {}) if isinstance(udm_event, dict) else {}

    if not isinstance(metadata, dict):
        metadata = {}
    if not isinstance(security_result, dict):
        security_result = {}
    if not isinstance(extensions, dict):
        extensions = {}
    if not isinstance(additional, dict):
        additional = {}

    return {
        "collection_source": _get_udm_event_sources(udm_event),
        "event_type": metadata.get("event_type"),
        "product_event_type": metadata.get("product_event_type"),
        "product_log_id": metadata.get("product_log_id"),
        "source_severity": extensions.get("severity"),
        "soar_severity": security_result.get("severity"),
        "merged_record_count": extensions.get("_merged_record_count") or additional.get("_merged_record_count"),
        "extension_keys": sorted(extensions.keys()),
    }


def _log_udm_samples(
    logger: Any,
    udm_events: Any,
    is_test_run: bool,
    limit: int = 3,
) -> None:
    if not is_test_run:
        return

    for index, udm_event in enumerate((udm_events or [])[:limit], start=1):
        try:
            preview = json.dumps(_safe_udm_sample(udm_event), sort_keys=True, default=str)
        except Exception:
            preview = str(_safe_udm_sample(udm_event))
        logger.info(f"UDM safe sample #{index}: {preview}")


@output_handler
def main(is_test_run: bool) -> None:
    siemplify = SiemplifyConnectorExecution()
    siemplify.script_name = CONNECTOR_NAME
    alerts = []

    try:
        if is_test_run:
            siemplify.LOGGER.info("***** IDE test run *****")

        manager = SpyCloudManager(siemplify)

        device_product_field = extract_connector_param(
            siemplify,
            param_name="DeviceProductField",
            is_mandatory=False,
            print_value=True,
        )
        environment_field_name = extract_connector_param(
            siemplify,
            param_name="Environment Field Name",
            default_value="",
            input_type=str,
            print_value=True,
        )
        environment_regex_pattern = extract_connector_param(
            siemplify,
            param_name="Environment Regex Pattern",
            input_type=str,
            print_value=True,
        )
        environment_common = GetEnvironmentCommonFactory.create_environment_manager(
            siemplify,
            environment_field_name,
            environment_regex_pattern,
        )

        # When enabled, plaintext passwords and other sensitive breach fields are
        # persisted onto the case events instead of being stripped. This retains
        # secrets permanently in SecOps case storage; it defaults to off and should
        # only be turned on with explicit sign-off.
        include_secrets = extract_connector_param(
            siemplify,
            param_name="Include Plaintext Secrets",
            default_value=False,
            input_type=bool,
            print_value=True,
        )
        if include_secrets:
            siemplify.LOGGER.warn(
                "Include Plaintext Secrets is ENABLED: plaintext passwords and other "
                "sensitive breach fields will be persisted onto case events."
            )

        if is_test_run:
            # TEMP DIAGNOSTIC (revert after the no-new-records issue is fixed):
            # instead of the ping-only connectivity check, attempt a bounded real
            # data pull and log why records may not be flowing. Still
            # non-destructive: no alerts created, no checkpoints saved.
            manager.diagnostic_pull()
            siemplify.LOGGER.info(
                "Diagnostic test run completed. Review the DIAG log lines above. "
                "No alerts were created and no checkpoints were updated."
            )
            siemplify.return_package([])
            return

        raw_records, checkpoint_until = manager.main(is_test_run=False)
        raw_records = raw_records or []

        siemplify.LOGGER.info(f"Fetched {len(raw_records)} raw SpyCloud records")
        siemplify.LOGGER.info(
            "Raw SpyCloud record source counts: "
            f"{_format_source_counts(_count_sources(raw_records, _get_raw_record_sources))}"
        )

        if not raw_records:
            siemplify.LOGGER.info("No SpyCloud records returned for the requested time window")
            siemplify.return_package([])
            # Nothing to deliver, but any drained-empty modification window /
            # Compass daily gate is valid progress and should be committed.
            manager.commit_pending()
            return

        # Breach catalog enrichment (integration guide 9.1.2 Option A): a cached,
        # source_id-scoped index. This does NOT download the full global catalog
        # every cycle; it lazily caches only the sources we actually see.
        breach_catalog_by_id = {}
        try:
            breach_catalog_by_id = manager.get_breach_catalog_index(raw_records) or {}
        except Exception as e:
            siemplify.LOGGER.error(f"Breach catalog enrichment failed. Continuing without enrichment. Error: {e}")
            breach_catalog_by_id = {}

        converter = SpyCloudUdmConverter(include_secrets=include_secrets)

        udm_events = converter.convert_records(
            records=raw_records,
            breach_catalog_by_id=breach_catalog_by_id,
            merge_endpoint_by_log_id=True,
        )

        siemplify.LOGGER.info(f"Converted {len(udm_events)} UDM events")
        siemplify.LOGGER.info(
            "UDM event source counts after conversion/merge: "
            f"{_format_source_counts(_count_sources(udm_events, _get_udm_event_sources))}"
        )
        _log_udm_samples(siemplify.LOGGER, udm_events, is_test_run=is_test_run)

        if not udm_events:
            siemplify.LOGGER.info("No UDM events were produced from the fetched SpyCloud records")
            siemplify.return_package([])
            manager.commit_pending()
            return

        for index, udm_event in enumerate(udm_events, start=1):
            try:
                security_result = udm_event.get("security_result", {})
                metadata = udm_event.get("metadata", {})
                additional = udm_event.get("additional", {})
                extensions = udm_event.get("extensions", {})

                soar_severity = security_result.get("severity")
                risk_score = security_result.get("risk_score")
                criticality = security_result.get("criticality")
                product_severity = security_result.get("product_severity")
                product_priority = security_result.get("product_priority")
                severity_label = additional.get("spycloud_severity_label") or extensions.get("spycloud_severity_label")
                source_severity = extensions.get("severity")
                product_log_id = metadata.get("product_log_id")
                event_type = metadata.get("event_type")
                collection_source = _get_udm_event_sources(udm_event)
                merged_record_count = extensions.get("_merged_record_count") or additional.get("_merged_record_count")

                # Sample per-record logging. High-volume modification pulls can
                # produce thousands of events per cycle; logging every one is a
                # significant contributor to hitting the connector timeout.
                if index <= 10 or index % 500 == 0:
                    siemplify.LOGGER.info(
                    "Building alert #{idx}: "
                    "event_type={event_type}, "
                    "product_log_id={product_log_id}, "
                    "collection_source={collection_source}, "
                    "merged_record_count={merged_record_count}, "
                    "source_severity={source_severity}, "
                    "severity_label={severity_label}, "
                    "soar_severity={soar_severity}, "
                    "risk_score={risk_score}, "
                    "criticality={criticality}, "
                    "product_severity={product_severity}, "
                    "product_priority={product_priority}".format(
                        idx=index,
                        event_type=event_type,
                        product_log_id=product_log_id,
                        collection_source=collection_source,
                        merged_record_count=merged_record_count,
                        source_severity=source_severity,
                        severity_label=severity_label,
                        soar_severity=soar_severity,
                        risk_score=risk_score,
                        criticality=criticality,
                        product_severity=product_severity,
                        product_priority=product_priority,
                    )
                )

                alert = build_alert_from_udm_event(
                    udm_event,
                    environment_common=environment_common,
                    device_product_field=device_product_field,
                )

                if not alert:
                    siemplify.LOGGER.error(
                        f"Parser returned an empty alert object for product_log_id={product_log_id}"
                    )
                    continue

                alerts.append(alert)

            except Exception as e:
                try:
                    preview = json.dumps(udm_event, default=str)[:2000]
                except Exception:
                    preview = str(udm_event)[:2000]

                siemplify.LOGGER.error(
                    f"Failed to process UDM event #{index} into alert: {e}. "
                    f"UDM preview: {preview}"
                )

        siemplify.LOGGER.info(f"Created {len(alerts)} alerts")
        siemplify.LOGGER.info(
            "Alert source counts after parser packaging: "
            f"{_format_source_counts(_count_sources(alerts, _get_alert_sources))}"
        )

        siemplify.return_package(alerts)

        # Commit progress ONLY after successful delivery (integration guide 9.2):
        # advance the publish-date checkpoint and flush deferred modification/
        # Compass progress. If any step above raised, we hit the except branch,
        # return an empty package, and commit nothing, so undelivered records are
        # re-fetched next cycle rather than skipped.
        if not is_test_run and checkpoint_until:
            checkpoint_ms = manager.checkpoint_manager.iso_to_epoch_ms(checkpoint_until)
            manager.checkpoint_manager.save_checkpoint(checkpoint_ms)
            siemplify.LOGGER.info(f"Saved checkpoint at {checkpoint_until}")
        manager.commit_pending()

    except Exception as e:
        siemplify.LOGGER.error(f"Connector execution failed: {e}")
        siemplify.return_package([])


if __name__ == "__main__":
    is_test_run = not (len(sys.argv) < 2 or sys.argv[1] == "True")
    main(is_test_run)