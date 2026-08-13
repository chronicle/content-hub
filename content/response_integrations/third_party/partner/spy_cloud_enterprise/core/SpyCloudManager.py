from __future__ import annotations

import json
import time
from datetime import datetime, timedelta, timezone
from typing import Any

from TIPCommon.extraction import extract_connector_param

from .CheckpointManager import CheckpointManager
from .Constants import ENDPOINT_BREACH_DATA_WATCHLIST, ENDPOINT_PING
from .SpyCloudSDK import SpyCloudSDK

SPYCLOUD_API_KEY = "API Key"
ENABLE_COMPASS = "Enable Compass"
SEVERITIES = "SEVERITIES"
VERIFY_SSL = "Verify SSL"
API_ROOT = "API Root"

MAX_WATCHLIST_WINDOW_HOURS = 2
MAX_COMPASS_WINDOW_HOURS = 2
COMPASS_LAST_RUN_DATE_KEY = "compass_last_run_date"

MAX_WATCHLIST_MODIFICATION_WINDOW_HOURS = 2
WATCHLIST_MODIFICATION_LAST_RUN_DATE_KEY = "watchlist_modification_last_run_date"
WATCHLIST_MODIFICATION_CHECKPOINT_KEY = "watchlist_modification_checkpoint"

# Resumable-drain state for the once-daily modification pull. SpyCloud's
# modification endpoint can return hundreds of thousands of records per day
# (guide: "newly cracked passwords"), far more than a SecOps dynamic-script
# connector can fetch + convert + package within its hard ~59s timeout. We keep
# the guide's semantics (once per calendar day, 2-hour windows, cursor
# pagination) but drain a bounded slice per connector cycle and persist progress
# so the next cycle resumes instead of restarting or timing out.
WATCHLIST_MODIFICATION_WINDOW_UNTIL_KEY = "watchlist_modification_window_until"
WATCHLIST_MODIFICATION_CURSOR_SINCE_KEY = "watchlist_modification_cursor_since"
WATCHLIST_MODIFICATION_CURSOR_KEY = "watchlist_modification_cursor"

# Per-cycle bounds. The record cap normally binds first and keeps the volume
# handed to UDM conversion + return_package small enough to finish well inside
# the connector timeout. The time budget is a wall-clock backstop covering all
# fetching (publish-date pull + modification drain) so that the remaining time
# in the ~59s SecOps cycle is reserved for catalog enrichment, UDM conversion,
# and return_package.
MODIFICATION_MAX_RECORDS_PER_CYCLE = 1500
MODIFICATION_TIME_BUDGET_SECONDS = 25

# Breach catalog enrichment (integration guide 9.1.2 Option A: cache the catalog
# locally and join on source_id). We never download the full global catalog;
# instead we lazily fetch the catalog entry for each source_id we encounter and
# cache it in connector context, bounded per cycle so enrichment stays inside
# the connector timeout. Enrichment is best-effort: a record whose source is not
# yet cached is still ingested, just without breach title/category until a later
# cycle warms the cache.
BREACH_CATALOG_CACHE_KEY = "breach_catalog_cache"
BREACH_CATALOG_MAX_FETCH_PER_CYCLE = 15
BREACH_CATALOG_FETCH_BUDGET_SECONDS = 8
# Cap the persisted cache so the connector-context value stays bounded. A single
# Watchlist references a limited set of breach sources, so this is generous;
# oldest-inserted entries are dropped first if exceeded.
BREACH_CATALOG_MAX_ENTRIES = 5000
# Minimal fields kept per source (guide 9.1.2: breach title + breach_main_category),
# plus a few others the UDM converter surfaces from the catalog entry.
BREACH_CATALOG_CACHE_FIELDS = (
    "id",
    "source_id",
    "title",
    "short_title",
    "breach_main_category",
    "breach_category",
    "confidence",
    "site",
    "description",
    "tlp",
    "service",
    "published_date",
    "breach_date",
)

SOURCE_WATCHLIST_MODIFICATION = "watchlist_modification"

COLLECTION_SOURCE_FIELD = "spycloud_collection_source"
SOURCE_WATCHLIST = "watchlist"
SOURCE_COMPASS = "compass"

WATCHLIST_ENDPOINT = "/enterprise-v2/breach/data/watchlist"
COMPASS_ENDPOINT = "/enterprise-v2/compass/data"

SAFE_SAMPLE_FIELDS = [
    COLLECTION_SOURCE_FIELD,
    "document_id",
    "source_id",
    "severity",
    "log_id",
    "infected_machine_id",
    "target_domain",
    "target_subdomain",
    "spycloud_publish_date",
    "infected_time",
    "record_modification_date",
    "record_cracked_date",
    "record_addition_date",
    "malware_family",
]

SENSITIVE_KEY_FRAGMENTS = (
    "password",
    "cookie",
    "token",
    "secret",
    "credential",
    "private_key",
    "cc_",
    "bank_",
    "taxid",
    "ssn",
    "national_id",
)


class SpyCloudManager:
    def __init__(self, siemplify: Any) -> None:
        self.siemplify = siemplify
        self.checkpoint_manager = CheckpointManager(self.siemplify)

        # Connector runs use a SiemplifyConnectorExecution object, which does
        # not expose get/set_script_property (those live on SiemplifyAction).
        # Persist per-connector state through the connector context property
        # API instead, keyed by the connector identifier.
        try:
            self._context_identifier = (
                self.siemplify.context.connector_info.identifier
            )
        except AttributeError:
            self._context_identifier = self.siemplify.script_name

        api_key = extract_connector_param(
            self.siemplify,
            param_name=SPYCLOUD_API_KEY,
            is_mandatory=True,
            print_value=False,
        )

        api_root = extract_connector_param(
            self.siemplify,
            param_name=API_ROOT,
            is_mandatory=True,
            input_type=str,
            print_value=True,
        )

        enable_compass = extract_connector_param(
            self.siemplify,
            param_name=ENABLE_COMPASS,
            is_mandatory=False,
            input_type=bool,
            default_value=False,
            print_value=True,
        )

        severities = extract_connector_param(
            self.siemplify,
            param_name=SEVERITIES,
            is_mandatory=False,
            print_value=True,
        )

        verify_ssl = extract_connector_param(
            self.siemplify,
            param_name=VERIFY_SSL,
            is_mandatory=False,
            default_value=True,
            input_type=bool,
            print_value=True,
        )

        self.api_root = api_root
        self.enable_compass = bool(enable_compass)
        self.verify_ssl = verify_ssl

        self.severities = []
        if severities:
            for raw_severity in str(severities).split(","):
                cleaned = raw_severity.strip()
                if not cleaned:
                    continue
                try:
                    self.severities.append(int(cleaned))
                except ValueError:
                    self.siemplify.LOGGER.warning(
                        f"Invalid severity value '{cleaned}' ignored. "
                        "Please ensure only integers are configured."
                    )

        self.siemplify.LOGGER.info(
            "SpyCloud manager configuration parsed. "
            f"enable_compass={self.enable_compass}, severities={self.severities}, "
            f"verify_ssl={self.verify_ssl}"
        )

        self.sdk = SpyCloudSDK(
            api_key,
            base_url=self.api_root,
            verify_ssl=self.verify_ssl,
        )

        # Progress (modification-drain cursor/window, Compass daily gate) is
        # queued here during a cycle and only persisted via commit_pending()
        # after return_package succeeds, so a mid-cycle failure re-delivers
        # rather than skips records (integration guide 9.2).
        self._pending_context_writes: list[tuple[str, str]] = []
        self._modification_drain_in_progress = False

    def _parse_iso_z(self, value: str) -> datetime:
        return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)

    def _format_iso_z(self, value: datetime) -> str:
        return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    def _format_compass_date_param(self, value: str) -> str:
        """
        The Compass data endpoint currently accepts date-only since/until values
        in YYYY-MM-DD format. Watchlist continues to use full ISO timestamps.
        """
        if value in (None, ""):
            return value

        try:
            return self._parse_iso_z(value).date().isoformat()
        except Exception:
            # Fall back to the leading date portion. This keeps the request
            # date-only even if a future caller provides a slightly different
            # timestamp format.
            return str(value).strip()[:10]

    def _build_time_chunks(self, since: str, until: str, max_hours: int):
        start = self._parse_iso_z(since)
        end = self._parse_iso_z(until)

        chunks = []
        current = start

        while current < end:
            chunk_end = min(current + timedelta(hours=max_hours), end)
            chunks.append((
                self._format_iso_z(current),
                self._format_iso_z(chunk_end)
            ))
            current = chunk_end

        return chunks

    def _get_context_property(self, key: str):
        return self.siemplify.get_connector_context_property(
            self._context_identifier, key
        )

    def _set_context_property(self, key: str, value: str):
        self.siemplify.set_connector_context_property(
            self._context_identifier, key, value
        )

    def _defer_context_property(self, key: str, value: str):
        """
        Queue a connector-context write to be committed only after this cycle's
        records have been successfully delivered (see commit_pending). Keeps
        modification-drain / Compass progress from advancing ahead of delivery.
        """
        self._pending_context_writes = [
            (k, v) for (k, v) in self._pending_context_writes if k != key
        ]
        self._pending_context_writes.append((key, value))

    def commit_pending(self):
        """Persist deferred progress. Call only after return_package succeeds."""
        for key, value in self._pending_context_writes:
            self._set_context_property(key, value)
        self._pending_context_writes = []

    def _load_compass_last_run_date(self):
        return self._get_context_property(COMPASS_LAST_RUN_DATE_KEY)

    def _save_compass_last_run_date(self, value: str):
        self._set_context_property(COMPASS_LAST_RUN_DATE_KEY, value)

    def _should_run_compass_today(self) -> bool:
        today = datetime.now(timezone.utc).date().isoformat()
        last_run_date = self._load_compass_last_run_date()

        self.siemplify.LOGGER.info(
            f"Compass daily gate check. last_run_date={last_run_date}, today={today}"
        )

        return last_run_date != today

    def _load_watchlist_modification_last_run_date(self):
        return self._get_context_property(WATCHLIST_MODIFICATION_LAST_RUN_DATE_KEY)

    def _save_watchlist_modification_last_run_date(self, value: str):
        self._set_context_property(WATCHLIST_MODIFICATION_LAST_RUN_DATE_KEY, value)

    def _should_run_watchlist_modification_today(self) -> bool:
        today = datetime.now(timezone.utc).date().isoformat()
        last_run_date = self._load_watchlist_modification_last_run_date()

        self.siemplify.LOGGER.info(
            "Watchlist modification daily gate check. "
            f"last_run_date={last_run_date}, today={today}"
        )

        return last_run_date != today

    def _load_watchlist_modification_checkpoint(self):
        return self._get_context_property(WATCHLIST_MODIFICATION_CHECKPOINT_KEY)

    def _save_watchlist_modification_checkpoint(self, value: str):
        self._set_context_property(WATCHLIST_MODIFICATION_CHECKPOINT_KEY, value)

    def _get_watchlist_modification_time_window(self):
        """
        Separate checkpoint for once-daily modified-record ingestion.

        Initial run uses the same 24-hour lookback behavior as the normal connector.
        Subsequent runs continue from the saved modification checkpoint.
        """
        checkpoint_value = self._load_watchlist_modification_checkpoint()
        now = datetime.now(timezone.utc)
        until = self._format_iso_z(now)

        if not checkpoint_value:
            since = self._format_iso_z(now - timedelta(hours=24))
            return since, until

        try:
            since_dt = self._parse_iso_z(checkpoint_value) + timedelta(seconds=1)
            since = self._format_iso_z(since_dt)
            return since, until
        except Exception:
            self.siemplify.LOGGER.error(
                "Invalid Watchlist modification checkpoint found. "
                "Falling back to a 24-hour modification lookback."
            )
            since = self._format_iso_z(now - timedelta(hours=24))
            return since, until

    def _is_sensitive_key(self, key) -> bool:
        key_lower = str(key).lower()
        return any(fragment in key_lower for fragment in SENSITIVE_KEY_FRAGMENTS)

    def _safe_record_preview(self, record):
        if not isinstance(record, dict):
            return {"type": type(record).__name__}

        preview = {
            key: record.get(key)
            for key in SAFE_SAMPLE_FIELDS
            if key in record and not self._is_sensitive_key(key)
        }
        preview["non_sensitive_keys"] = sorted(
            str(key) for key in record.keys() if not self._is_sensitive_key(key)
        )[:50]
        return preview

    def _log_safe_samples(self, label: str, records, is_test_run: bool, limit: int = 3):
        if not is_test_run:
            return

        records = records or []
        for index, record in enumerate(records[:limit], start=1):
            try:
                preview = json.dumps(self._safe_record_preview(record), sort_keys=True, default=str)
            except Exception:
                preview = str(self._safe_record_preview(record))

            self.siemplify.LOGGER.info(
                f"{label} safe sample #{index}: {preview}"
            )

    def _tag_records(self, records, source: str):
        tagged_records = []
        for record in records or []:
            if isinstance(record, dict):
                tagged_record = dict(record)
                tagged_record[COLLECTION_SOURCE_FIELD] = source
                tagged_records.append(tagged_record)
            else:
                tagged_records.append(record)
        return tagged_records

    def get_time_window(self):
        return self.checkpoint_manager.get_next_since_until()

    def _run_watchlist(self, since: str, until: str, is_test_run: bool = False):
        response = []

        watchlist_chunks = self._build_time_chunks(
            since=since,
            until=until,
            max_hours=MAX_WATCHLIST_WINDOW_HOURS
        )

        self.siemplify.LOGGER.info(
            "Watchlist collection plan. "
            f"endpoint={WATCHLIST_ENDPOINT}, chunks={len(watchlist_chunks)}, "
            f"window={since} -> {until}, severities={self.severities}"
        )

        for index, (chunk_since, chunk_until) in enumerate(watchlist_chunks, start=1):
            self.siemplify.LOGGER.info(
                "Fetching Watchlist chunk from "
                f"{WATCHLIST_ENDPOINT}: chunk={index}/{len(watchlist_chunks)}, "
                f"since={chunk_since}, until={chunk_until}, severities={self.severities}"
            )

            chunk_response = self.sdk.breach_data.watchlist(
                since=chunk_since,
                until=chunk_until,
                severities=self.severities
            ) or []
            tagged_chunk_response = self._tag_records(chunk_response, SOURCE_WATCHLIST)
            response.extend(tagged_chunk_response)

            self.siemplify.LOGGER.info(
                f"Watchlist chunk {index}/{len(watchlist_chunks)} returned "
                f"{len(tagged_chunk_response)} record(s)"
            )
            self._log_safe_samples(
                label=f"Watchlist chunk {index}/{len(watchlist_chunks)}",
                records=tagged_chunk_response,
                is_test_run=is_test_run,
                limit=1,
            )

        self.siemplify.LOGGER.info(f"Watchlist total returned {len(response)} record(s)")
        return response

    def _complete_watchlist_modification_window(self, window_until: str):
        """Mark the current daily modification window fully drained (deferred)."""
        today = datetime.now(timezone.utc).date().isoformat()
        self._defer_context_property(WATCHLIST_MODIFICATION_LAST_RUN_DATE_KEY, today)
        self._defer_context_property(WATCHLIST_MODIFICATION_CHECKPOINT_KEY, window_until)
        self._defer_context_property(WATCHLIST_MODIFICATION_WINDOW_UNTIL_KEY, "")
        self._defer_context_property(WATCHLIST_MODIFICATION_CURSOR_SINCE_KEY, "")
        self._defer_context_property(WATCHLIST_MODIFICATION_CURSOR_KEY, "")
        self.siemplify.LOGGER.info(
            "Watchlist modification daily pull completed. "
            f"Will save (on delivery) last_run_date={today}, checkpoint={window_until}"
        )

    def _drain_watchlist_modification(self, deadline_monotonic: float, is_test_run: bool = False):
        """
        Cursor-resumable, time-budgeted once-daily modification pull.

        Follows the integration guide (once per calendar day, 2-hour windows,
        cursor pagination) but only fetches a bounded slice per connector cycle
        so the connector always returns before the ~59s SecOps timeout. Progress
        (window, current chunk, cursor) is persisted to connector context after
        every page, so the next cycle resumes exactly where this one stopped.

        Returns the records fetched this cycle.

        Progress (window, current chunk, cursor) is tracked in local variables
        during the cycle and only *deferred* for persistence (committed after
        return_package succeeds), so a mid-cycle timeout re-delivers the same
        slice on the next cycle instead of advancing past undelivered records.
        """
        self._modification_drain_in_progress = False
        window_until = self._get_context_property(WATCHLIST_MODIFICATION_WINDOW_UNTIL_KEY)

        if not window_until:
            # No drain in progress. Guardrail: start at most once per calendar day.
            if not self._should_run_watchlist_modification_today():
                self.siemplify.LOGGER.info(
                    "Skipping Watchlist modification pull because it already ran today."
                )
                return []
            window_since, window_until = self._get_watchlist_modification_time_window()
            cursor_since = window_since
            cursor = ""
            self.siemplify.LOGGER.info(
                "Watchlist modification daily pull starting. "
                f"window={window_since} -> {window_until}, "
                f"severities={self.severities}"
            )
        else:
            cursor_since = self._get_context_property(WATCHLIST_MODIFICATION_CURSOR_SINCE_KEY)
            cursor = self._get_context_property(WATCHLIST_MODIFICATION_CURSOR_KEY) or ""
            self.siemplify.LOGGER.info(
                "Resuming in-progress Watchlist modification drain. "
                f"window_until={window_until}, cursor_since={cursor_since}"
            )

        records = []
        fetched = 0
        completed = False

        while True:
            if fetched >= MODIFICATION_MAX_RECORDS_PER_CYCLE:
                self.siemplify.LOGGER.info(
                    f"Watchlist modification drain paused: per-cycle cap "
                    f"({MODIFICATION_MAX_RECORDS_PER_CYCLE}) reached; will resume next cycle."
                )
                break
            if time.monotonic() >= deadline_monotonic:
                self.siemplify.LOGGER.info(
                    "Watchlist modification drain paused: time budget reached; "
                    "will resume next cycle."
                )
                break

            if not cursor_since or self._parse_iso_z(cursor_since) >= self._parse_iso_z(window_until):
                completed = True
                break

            chunk_until_dt = min(
                self._parse_iso_z(cursor_since) + timedelta(hours=MAX_WATCHLIST_MODIFICATION_WINDOW_HOURS),
                self._parse_iso_z(window_until),
            )
            chunk_until = self._format_iso_z(chunk_until_dt)
            start_cursor = cursor or None
            remaining_cap = MODIFICATION_MAX_RECORDS_PER_CYCLE - fetched

            self.siemplify.LOGGER.info(
                "Fetching Watchlist modification page from "
                f"{WATCHLIST_ENDPOINT}: since_modification={cursor_since}, "
                f"until_modification={chunk_until}, severities={self.severities}, "
                f"resume_cursor={'yes' if start_cursor else 'no'}, max_records={remaining_cap}"
            )

            page, next_cursor = self.sdk.breach_data.watchlist_page(
                since_modification=cursor_since,
                until_modification=chunk_until,
                severities=self.severities,
                start_cursor=start_cursor,
                max_records=remaining_cap,
            )
            page = page or []
            tagged_page = self._tag_records(page, SOURCE_WATCHLIST_MODIFICATION)
            records.extend(tagged_page)
            fetched += len(tagged_page)

            if next_cursor:
                # More pages remain within this 2-hour chunk; resume from cursor.
                cursor = next_cursor
                self.siemplify.LOGGER.info(
                    f"Watchlist modification chunk partial: {len(tagged_page)} record(s) "
                    "this page; more pages remain in chunk."
                )
            else:
                # Chunk fully drained; advance to the next 2-hour chunk.
                cursor_since = chunk_until
                cursor = ""
                self.siemplify.LOGGER.info(
                    f"Watchlist modification chunk complete: {len(tagged_page)} record(s); "
                    f"advanced to {chunk_until}."
                )

        # Defer progress persistence until the records are actually delivered.
        if completed:
            self._complete_watchlist_modification_window(window_until)
        else:
            self._modification_drain_in_progress = True
            self._defer_context_property(WATCHLIST_MODIFICATION_WINDOW_UNTIL_KEY, window_until)
            self._defer_context_property(WATCHLIST_MODIFICATION_CURSOR_SINCE_KEY, cursor_since)
            self._defer_context_property(WATCHLIST_MODIFICATION_CURSOR_KEY, cursor)

        self._log_safe_samples(
            label="Watchlist modification",
            records=records,
            is_test_run=is_test_run,
            limit=1,
        )
        self.siemplify.LOGGER.info(
            f"Watchlist modification returned {len(records)} record(s) this cycle."
        )
        return records

    def _run_compass(self, since: str, until: str, is_test_run: bool = False):
        response = []

        compass_since = self._format_compass_date_param(since)
        compass_until = self._format_compass_date_param(until)

        self.siemplify.LOGGER.info(
            "Compass collection plan. "
            f"endpoint={COMPASS_ENDPOINT}, requests=1, "
            f"source_window={since} -> {until}, "
            f"api_date_window={compass_since} -> {compass_until}"
        )
        self.siemplify.LOGGER.info(
            "Compass API requires date-only parameters. "
            f"Converted since/until for Compass only: "
            f"since={compass_since}, until={compass_until}"
        )
        self.siemplify.LOGGER.info(
            "Fetching Compass data from "
            f"{COMPASS_ENDPOINT}: since={compass_since}, until={compass_until}"
        )

        chunk_response = self.sdk.compass.data(
            since=compass_since,
            until=compass_until
        ) or []
        tagged_chunk_response = self._tag_records(chunk_response, SOURCE_COMPASS)
        response.extend(tagged_chunk_response)

        self.siemplify.LOGGER.info(
            f"Compass request returned {len(tagged_chunk_response)} record(s)"
        )
        self._log_safe_samples(
            label="Compass request",
            records=tagged_chunk_response,
            is_test_run=is_test_run,
            limit=1,
        )

        self.siemplify.LOGGER.info(f"Compass total returned {len(response)} record(s)")
        return response

    def _load_breach_catalog_cache(self):
        raw = self._get_context_property(BREACH_CATALOG_CACHE_KEY)
        if not raw:
            return {}
        try:
            data = json.loads(raw)
            return data if isinstance(data, dict) else {}
        except Exception:
            self.siemplify.LOGGER.warning(
                "Breach catalog cache was unreadable; starting a fresh cache."
            )
            return {}

    def _save_breach_catalog_cache(self, cache):
        try:
            self._set_context_property(
                BREACH_CATALOG_CACHE_KEY, json.dumps(cache, default=str)
            )
        except Exception as e:
            self.siemplify.LOGGER.error(f"Failed to persist breach catalog cache: {e}")

    @staticmethod
    def _minimal_catalog_entry(entry):
        if not isinstance(entry, dict):
            return {}
        return {
            key: entry.get(key)
            for key in BREACH_CATALOG_CACHE_FIELDS
            if entry.get(key) not in (None, "", [], {})
        }

    def _distinct_source_ids(self, records):
        seen = []
        seen_set = set()
        for record in records or []:
            if not isinstance(record, dict):
                continue
            source_id = record.get("source_id")
            if source_id in (None, ""):
                continue
            key = str(source_id)
            if key not in seen_set:
                seen_set.add(key)
                seen.append(key)
        return seen

    def get_breach_catalog_index(self, records):
        """
        Build a source_id -> catalog-metadata index for enriching this cycle's
        records, following integration guide 9.1.2 Option A (cache the breach
        catalog locally and join on source_id).

        This never downloads the full global breach catalog (which is far larger
        than any single Watchlist). It lazily fetches only the catalog entries
        for source_ids present in this batch that are not yet cached, bounded per
        cycle so the connector stays within the SecOps ~59s timeout. The cache is
        persisted to connector context and warms over successive cycles.
        Enrichment is best-effort: a record whose source is not yet cached is
        still ingested this cycle, just without breach title/category.
        """
        cache = self._load_breach_catalog_cache()
        source_ids = self._distinct_source_ids(records)
        missing = [sid for sid in source_ids if sid not in cache]

        fetched = 0
        deadline = time.monotonic() + BREACH_CATALOG_FETCH_BUDGET_SECONDS
        for source_id in missing:
            if fetched >= BREACH_CATALOG_MAX_FETCH_PER_CYCLE:
                self.siemplify.LOGGER.info(
                    f"Breach catalog enrichment: per-cycle fetch cap "
                    f"({BREACH_CATALOG_MAX_FETCH_PER_CYCLE}) reached; "
                    f"{len(missing) - fetched} source(s) will enrich on a later cycle."
                )
                break
            if time.monotonic() >= deadline:
                self.siemplify.LOGGER.info(
                    "Breach catalog enrichment: fetch time budget reached; "
                    "remaining sources will enrich on a later cycle."
                )
                break
            try:
                entry = self.sdk.breach_catalog.catalog_by_id(source_id)
            except Exception as e:
                self.siemplify.LOGGER.error(
                    f"Failed to fetch breach catalog entry for source_id={source_id}. "
                    f"Continuing without enrichment for it: {e}"
                )
                continue
            if entry:
                cache[source_id] = self._minimal_catalog_entry(entry)
                fetched += 1

        # Bound the persisted cache size (drop oldest-inserted entries first).
        if len(cache) > BREACH_CATALOG_MAX_ENTRIES:
            overflow = len(cache) - BREACH_CATALOG_MAX_ENTRIES
            for stale_key in list(cache.keys())[:overflow]:
                cache.pop(stale_key, None)

        # The catalog cache is additive and idempotent; committing it immediately
        # (rather than deferring) just avoids re-fetching on a later cycle and is
        # safe even if this cycle's delivery ultimately fails.
        if fetched:
            self._save_breach_catalog_cache(cache)

        index = {sid: cache[sid] for sid in source_ids if sid in cache}
        self.siemplify.LOGGER.info(
            f"Breach catalog enrichment: {len(source_ids)} distinct source(s) in batch, "
            f"{fetched} newly fetched, {len(index)} enriched from cache "
            f"(cache size {len(cache)})."
        )
        return index

    def test_connectivity(self):
        """
        Connectivity-only test run.

        This intentionally avoids Watchlist and Compass collection so published
        Content Hub test runs cannot bypass production since/until windows,
        Compass daily gating, or connector checkpoints.
        """
        self.siemplify.LOGGER.info(
            "Test run connectivity check. Pinging SpyCloud breach catalog endpoint: "
            f"{ENDPOINT_PING}"
        )
        self.sdk.breach_catalog.ping()
        self.siemplify.LOGGER.info(
            "Successfully connected to SpyCloud breach catalog. "
            "No Watchlist data, Compass data, breach records, alerts, or checkpoints "
            "are processed during connector test runs."
        )
        return True

    # ------------------------------------------------------------------ #
    # TEMP DIAGNOSTIC (revert after the no-new-records issue is resolved)
    # ------------------------------------------------------------------ #
    def diagnostic_pull(self):
        """
        TEMPORARY diagnostic used to figure out why the connector has not pulled
        new Watchlist records for several days even though Ping succeeds.

        Non-destructive: it does NOT save checkpoints, does NOT advance the
        modification drain, and does NOT create alerts. It attempts a bounded,
        real data pull against the current production window and logs everything
        an operator needs to see. Each step is independently guarded so one
        failure still lets the rest run.

        Revert this method (and its call site in the connector) once fixed.
        """
        log = self.siemplify.LOGGER
        DIAGNOSTIC_MAX_RECORDS = 200

        log.info("===== SpyCloud DIAGNOSTIC test run START =====")
        log.info(f"severities filter = {self.severities}")
        log.info(f"enable_compass = {self.enable_compass}, api_root = {self.api_root}")

        # 1) Connectivity (same check the normal test run does).
        try:
            self.sdk.breach_catalog.ping()
            log.info("DIAG step 1 connectivity: ping OK")
        except Exception as e:
            log.error(f"DIAG step 1 connectivity: ping FAILED: {e}")

        # 2) Current production window + how far behind the checkpoint is.
        since = until = None
        try:
            raw_checkpoint = self.checkpoint_manager.load_checkpoint()
            since, until = self.get_time_window()
            log.info(
                f"DIAG step 2 window: raw_checkpoint={raw_checkpoint}, "
                f"since={since}, until={until}"
            )
            try:
                span_hours = (
                    self._parse_iso_z(until) - self._parse_iso_z(since)
                ).total_seconds() / 3600.0
                chunks = self._build_time_chunks(since, until, MAX_WATCHLIST_WINDOW_HOURS)
                log.info(
                    f"DIAG step 2 window span = {span_hours:.1f}h, which builds "
                    f"{len(chunks)} x {MAX_WATCHLIST_WINDOW_HOURS}h watchlist chunk(s). "
                    "A large chunk count is the smoking gun for a stuck-checkpoint "
                    "timeout spiral (window grows each cycle, full drain never "
                    "finishes inside the 59s limit, checkpoint never advances)."
                )
            except Exception as e:
                log.error(f"DIAG step 2 chunk math FAILED: {e}")
        except Exception as e:
            log.error(f"DIAG step 2 window: FAILED to compute window: {e}")

        def _severities_in(records):
            return sorted(
                {r.get("severity") for r in records if isinstance(r, dict)},
                key=lambda v: (v is None, v),
            )

        # 3) PUBLISH-DATE pull over the FULL window (one bounded page), filtered.
        #    This is what the regular connector pull (_run_watchlist) uses.
        if since and until:
            try:
                page, next_cursor = self.sdk.breach_data.watchlist_page(
                    since=since,
                    until=until,
                    severities=self.severities,
                    max_records=DIAGNOSTIC_MAX_RECORDS,
                )
                page = page or []
                log.info(
                    f"DIAG step 3 PUBLISH-date filtered [{since} -> {until}] "
                    f"severities={self.severities}: returned {len(page)} record(s) "
                    f"(bounded at {DIAGNOSTIC_MAX_RECORDS}); "
                    f"more_pages={'yes' if next_cursor else 'no'}"
                )
                self._log_safe_samples(
                    label="DIAG publish filtered", records=page, is_test_run=True, limit=2
                )
            except Exception as e:
                log.error(f"DIAG step 3 PUBLISH-date filtered FAILED: {e}")

            # 4) Same publish-date window, UNFILTERED.
            try:
                page_all, _ = self.sdk.breach_data.watchlist_page(
                    since=since,
                    until=until,
                    severities=None,
                    max_records=DIAGNOSTIC_MAX_RECORDS,
                )
                page_all = page_all or []
                log.info(
                    f"DIAG step 4 PUBLISH-date UNFILTERED [{since} -> {until}]: "
                    f"returned {len(page_all)} record(s); "
                    f"severities present = {_severities_in(page_all)}"
                )
            except Exception as e:
                log.error(f"DIAG step 4 PUBLISH-date UNFILTERED FAILED: {e}")

            # 5) MODIFICATION-date pull over the same window (one bounded page),
            #    filtered. This is the path that catches records newly added to /
            #    modified in the catalog (the once-daily drain uses it). Records
            #    that appear "new in the catalog" but have an old publish date only
            #    show up here, NOT in steps 3/4.
            try:
                page_mod, next_mod = self.sdk.breach_data.watchlist_page(
                    since_modification=since,
                    until_modification=until,
                    severities=self.severities,
                    max_records=DIAGNOSTIC_MAX_RECORDS,
                )
                page_mod = page_mod or []
                log.info(
                    f"DIAG step 5 MODIFICATION-date filtered [{since} -> {until}] "
                    f"severities={self.severities}: returned {len(page_mod)} record(s) "
                    f"(bounded at {DIAGNOSTIC_MAX_RECORDS}); "
                    f"more_pages={'yes' if next_mod else 'no'}. "
                    "If this is >0 while steps 3/4 are 0, the expected records are "
                    "arriving by MODIFICATION date, not publish date -> the regular "
                    "publish-date pull cannot see them; only the once-daily "
                    "modification drain can."
                )
                self._log_safe_samples(
                    label="DIAG modification filtered", records=page_mod, is_test_run=True, limit=2
                )
            except Exception as e:
                log.error(f"DIAG step 5 MODIFICATION-date filtered FAILED: {e}")

            # 6) Same modification-date window, UNFILTERED.
            try:
                page_mod_all, _ = self.sdk.breach_data.watchlist_page(
                    since_modification=since,
                    until_modification=until,
                    severities=None,
                    max_records=DIAGNOSTIC_MAX_RECORDS,
                )
                page_mod_all = page_mod_all or []
                log.info(
                    f"DIAG step 6 MODIFICATION-date UNFILTERED [{since} -> {until}]: "
                    f"returned {len(page_mod_all)} record(s); "
                    f"severities present = {_severities_in(page_mod_all)}"
                )
            except Exception as e:
                log.error(f"DIAG step 6 MODIFICATION-date UNFILTERED FAILED: {e}")

        # ---- RAW request envelope probes -------------------------------- #
        # Steps 3-6 go through pagination + tagging, which hides what the API
        # actually returned. These probes hit the endpoint directly and log the
        # exact URL, HTTP status, and response envelope (hits/results/cursor) so
        # we can see whether the API itself is returning an empty set and why.
        def _diag_raw(step_label, params):
            try:
                resp = self.sdk._handler.get(ENDPOINT_BREACH_DATA_WATCHLIST, params=params)
                url = getattr(resp.request, "url", "?")
                log.info(f"{step_label}: HTTP {resp.status_code}  url={url}")
                try:
                    body = resp.json()
                except Exception:
                    log.info(f"{step_label} non-JSON body preview: {str(resp.text)[:500]}")
                    return
                if isinstance(body, dict):
                    results = body.get("results") or []
                    log.info(
                        f"{step_label} envelope: hits={body.get('hits')}, "
                        f"results_len={len(results)}, "
                        f"cursor={'yes' if body.get('cursor') else 'no'}, "
                        f"top_level_keys={sorted(body.keys())}"
                    )
                else:
                    log.info(f"{step_label} unexpected body type: {type(body).__name__}: {str(body)[:300]}")
            except Exception as e:
                log.error(f"{step_label} FAILED: {e}")

        # 8) NO date filter at all. If this returns data but steps 3/9 do not, the
        #    since/until params are the problem (format/semantics). If this is also
        #    empty, the endpoint/watchlist/auth-scope is the problem.
        _diag_raw("DIAG step 8 RAW no-params", {})

        # 9) RAW publish-date window (unfiltered), same params the connector sends.
        if since and until:
            _diag_raw("DIAG step 9 RAW publish-date", {"since": since, "until": until})
            # 10) RAW modification-date window (unfiltered).
            _diag_raw(
                "DIAG step 10 RAW modification-date",
                {"since_modification": since, "until_modification": until},
            )
            # 11) RAW date-only window. Some SpyCloud endpoints expect YYYY-MM-DD
            #     rather than a full ISO timestamp; if this returns data but step 9
            #     does not, the timestamp format is being rejected/misread.
            _diag_raw(
                "DIAG step 11 RAW publish-date date-only",
                {"since": since[:10], "until": until[:10]},
            )

        # 7) Modification-drain persisted state (in case that path is stuck too).
        try:
            log.info(
                "DIAG step 7 modification state: "
                f"last_run_date={self._get_context_property(WATCHLIST_MODIFICATION_LAST_RUN_DATE_KEY)}, "
                f"checkpoint={self._get_context_property(WATCHLIST_MODIFICATION_CHECKPOINT_KEY)}, "
                f"window_until={self._get_context_property(WATCHLIST_MODIFICATION_WINDOW_UNTIL_KEY)}, "
                f"cursor_since={self._get_context_property(WATCHLIST_MODIFICATION_CURSOR_SINCE_KEY)}, "
                f"cursor_set={'yes' if self._get_context_property(WATCHLIST_MODIFICATION_CURSOR_KEY) else 'no'}"
            )
        except Exception as e:
            log.error(f"DIAG step 5 modification state FAILED: {e}")

        log.info("===== SpyCloud DIAGNOSTIC test run END (no checkpoints saved) =====")

    def _maybe_run_compass(self, since: str, until: str):
        """Run the once-daily Compass pull if it has not already run today."""
        try:
            if self._should_run_compass_today():
                compass_response = self._run_compass(
                    since=since,
                    until=until,
                    is_test_run=False,
                )
                today = datetime.now(timezone.utc).date().isoformat()
                self._defer_context_property(COMPASS_LAST_RUN_DATE_KEY, today)
                self.siemplify.LOGGER.info(
                    f"Compass run completed. Will save (on delivery) last_run_date={today}"
                )
                return compass_response
            self.siemplify.LOGGER.info("Skipping Compass because it already ran today.")
        except Exception as e:
            self.siemplify.LOGGER.error(
                f"Failed to fetch Compass data. Treating as unavailable: {e}"
            )
        return []

    def main(self, is_test_run=False):
        if is_test_run:
            self.siemplify.LOGGER.info(
                "Test mode enabled. Running connectivity check only; skipping "
                "Watchlist collection, Watchlist fallback backfill, Compass collection, "
                "and checkpoint updates."
            )
            self.test_connectivity()
            return [], None

        # Wall-clock backstop so heavy once-daily pulls can never push the
        # connector past the SecOps hard timeout.
        fetch_deadline = time.monotonic() + MODIFICATION_TIME_BUDGET_SECONDS

        since, until = self.get_time_window()

        self.siemplify.LOGGER.info(f"since: {since}")
        self.siemplify.LOGGER.info(f"until: {until}")
        self.siemplify.LOGGER.info(f"severities: {self.severities}")
        self.siemplify.LOGGER.info(
            f"Compass enabled: {self.enable_compass}; is_test_run={is_test_run}"
        )

        response = []
        checkpoint_until = None

        watchlist_response = self._run_watchlist(
            since=since,
            until=until,
            is_test_run=False,
        )
        checkpoint_until = until

        response.extend(watchlist_response)

        modification_in_progress = False
        try:
            modification_response = self._drain_watchlist_modification(
                deadline_monotonic=fetch_deadline,
                is_test_run=False,
            )
            response.extend(modification_response)
            # A drain is still in progress if this cycle paused mid-window.
            # (Read the in-cycle flag, not context: progress is now deferred and
            # not yet persisted at this point.)
            modification_in_progress = self._modification_drain_in_progress
        except Exception as e:
            self.siemplify.LOGGER.error(
                f"Failed to fetch Watchlist modification data. "
                f"Continuing with normal Watchlist/Compass data: {e}"
            )

        # Defer Compass while a modification drain is mid-flight or the cycle's
        # time budget is spent, so the two heavy once-daily pulls don't compete
        # for the same connector cycle. Compass stays gated to once per day.
        if self.enable_compass:
            if modification_in_progress or time.monotonic() >= fetch_deadline:
                self.siemplify.LOGGER.info(
                    "Deferring Compass this cycle (modification drain in progress or "
                    "time budget spent); will attempt on a later cycle."
                )
            else:
                response.extend(self._maybe_run_compass(since, until))
        else:
            self.siemplify.LOGGER.info("Compass collection is disabled by connector configuration.")

        self._log_safe_samples(
            label="Combined SpyCloud raw records",
            records=response,
            is_test_run=is_test_run,
            limit=3,
        )

        self.siemplify.LOGGER.info(f"SpyCloud manager returning {len(response)} record(s)")
        return response, checkpoint_until
