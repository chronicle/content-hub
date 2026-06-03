import json
from datetime import datetime, timedelta, timezone

from .CheckpointManager import CheckpointManager
from .Constants import ENDPOINT_PING
from .SpyCloudSDK import SpyCloudSDK

SPYCLOUD_API_KEY = "SPYCLOUD_API_KEY"
ENABLE_COMPASS = "ENABLE_COMPASS"
SEVERITIES = "SEVERITIES"
VERIFY_SSL = "Verify SSL"

MAX_WATCHLIST_WINDOW_HOURS = 2
MAX_COMPASS_WINDOW_HOURS = 2
COMPASS_LAST_RUN_DATE_KEY = "compass_last_run_date"

MAX_WATCHLIST_MODIFICATION_WINDOW_HOURS = 2
WATCHLIST_MODIFICATION_LAST_RUN_DATE_KEY = "watchlist_modification_last_run_date"
WATCHLIST_MODIFICATION_CHECKPOINT_KEY = "watchlist_modification_checkpoint"

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
    def __init__(self, siemplify):
        self.siemplify = siemplify
        self.checkpoint_manager = CheckpointManager(self.siemplify)

        api_key = self.siemplify.extract_connector_param(
            param_name=SPYCLOUD_API_KEY,
            print_value=False
        )

        enable_compass = self.siemplify.extract_connector_param(
            param_name=ENABLE_COMPASS,
            print_value=True
        )

        severities = self.siemplify.extract_connector_param(
            param_name=SEVERITIES,
            print_value=True
        )

        verify_ssl = self.siemplify.extract_connector_param(
            param_name=VERIFY_SSL,
            default_value=True,
            input_type=bool,
            print_value=True,
        )

        self.enable_compass = str(enable_compass).strip().lower() == "true"
        self.verify_ssl = verify_ssl

        self.severities = []
        if severities:
            self.severities = [
                int(x.strip()) for x in str(severities).split(",") if x.strip()
            ]

        self.siemplify.LOGGER.info(
            "SpyCloud manager configuration parsed. "
            f"enable_compass={self.enable_compass}, severities={self.severities}, "
            f"verify_ssl={self.verify_ssl}"
        )

        self.sdk = SpyCloudSDK(api_key, verify_ssl=self.verify_ssl)

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

    def _load_compass_last_run_date(self):
        return self.siemplify.get_script_property(COMPASS_LAST_RUN_DATE_KEY)

    def _save_compass_last_run_date(self, value: str):
        self.siemplify.set_script_property(COMPASS_LAST_RUN_DATE_KEY, value)

    def _should_run_compass_today(self) -> bool:
        today = datetime.now(timezone.utc).date().isoformat()
        last_run_date = self._load_compass_last_run_date()

        self.siemplify.LOGGER.info(
            f"Compass daily gate check. last_run_date={last_run_date}, today={today}"
        )

        return last_run_date != today

    def _load_watchlist_modification_last_run_date(self):
        return self.siemplify.get_script_property(WATCHLIST_MODIFICATION_LAST_RUN_DATE_KEY)

    def _save_watchlist_modification_last_run_date(self, value: str):
        self.siemplify.set_script_property(WATCHLIST_MODIFICATION_LAST_RUN_DATE_KEY, value)

    def _should_run_watchlist_modification_today(self) -> bool:
        today = datetime.now(timezone.utc).date().isoformat()
        last_run_date = self._load_watchlist_modification_last_run_date()

        self.siemplify.LOGGER.info(
            "Watchlist modification daily gate check. "
            f"last_run_date={last_run_date}, today={today}"
        )

        return last_run_date != today

    def _load_watchlist_modification_checkpoint(self):
        return self.siemplify.get_script_property(WATCHLIST_MODIFICATION_CHECKPOINT_KEY)

    def _save_watchlist_modification_checkpoint(self, value: str):
        self.siemplify.set_script_property(WATCHLIST_MODIFICATION_CHECKPOINT_KEY, value)

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

    def _run_watchlist_modification(self, since: str, until: str, is_test_run: bool = False):
        response = []

        modification_chunks = self._build_time_chunks(
            since=since,
            until=until,
            max_hours=MAX_WATCHLIST_MODIFICATION_WINDOW_HOURS
        )

        self.siemplify.LOGGER.info(
            "Watchlist modification collection plan. "
            f"endpoint={WATCHLIST_ENDPOINT}, chunks={len(modification_chunks)}, "
            f"modification_window={since} -> {until}, severities={self.severities}"
        )

        for index, (chunk_since, chunk_until) in enumerate(modification_chunks, start=1):
            self.siemplify.LOGGER.info(
                "Fetching Watchlist modification chunk from "
                f"{WATCHLIST_ENDPOINT}: chunk={index}/{len(modification_chunks)}, "
                f"since_modification={chunk_since}, "
                f"until_modification={chunk_until}, "
                f"severities={self.severities}"
            )

            chunk_response = self.sdk.breach_data.watchlist(
                since_modification=chunk_since,
                until_modification=chunk_until,
                severities=self.severities
            ) or []

            tagged_chunk_response = self._tag_records(
                chunk_response,
                SOURCE_WATCHLIST_MODIFICATION
            )
            response.extend(tagged_chunk_response)

            self.siemplify.LOGGER.info(
                f"Watchlist modification chunk {index}/{len(modification_chunks)} "
                f"returned {len(tagged_chunk_response)} record(s)"
            )

            self._log_safe_samples(
                label=f"Watchlist modification chunk {index}/{len(modification_chunks)}",
                records=tagged_chunk_response,
                is_test_run=is_test_run,
                limit=1,
            )

        self.siemplify.LOGGER.info(
            f"Watchlist modification total returned {len(response)} record(s)"
        )
        return response

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

    def get_breach_catalog(self):
        """
        Fetch breach catalog entries for enrichment.
        For v1, pull the full catalog and let the converter join by source_id.
        Later, this can be cached in a script property or local file.
        """
        try:
            self.siemplify.LOGGER.info("Fetching breach catalog for enrichment")
            return self.sdk.breach_catalog.catalog()
        except Exception as e:
            self.siemplify.LOGGER.error(
                f"Failed to fetch breach catalog. Continuing without enrichment: {e}"
            )
            return []

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

    def main(self, is_test_run=False):
        if is_test_run:
            self.siemplify.LOGGER.info(
                "Test mode enabled. Running connectivity check only; skipping "
                "Watchlist collection, Watchlist fallback backfill, Compass collection, "
                "and checkpoint updates."
            )
            self.test_connectivity()
            return [], None

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

        try:
            if self._should_run_watchlist_modification_today():
                modification_since, modification_until = self._get_watchlist_modification_time_window()

                self.siemplify.LOGGER.info(
                    "Watchlist modification daily pull enabled for this run. "
                    f"modification_since={modification_since}, "
                    f"modification_until={modification_until}"
                )

                modification_response = self._run_watchlist_modification(
                    since=modification_since,
                    until=modification_until,
                    is_test_run=False,
                )
                response.extend(modification_response)

                today = datetime.now(timezone.utc).date().isoformat()
                self._save_watchlist_modification_last_run_date(today)
                self._save_watchlist_modification_checkpoint(modification_until)

                self.siemplify.LOGGER.info(
                    "Watchlist modification run completed. "
                    f"Saved last_run_date={today}, checkpoint={modification_until}"
                )
            else:
                self.siemplify.LOGGER.info(
                    "Skipping Watchlist modification pull because it already ran today."
                )
        except Exception as e:
            self.siemplify.LOGGER.error(
                f"Failed to fetch Watchlist modification data. "
                f"Continuing with normal Watchlist/Compass data: {e}"
            )

        if self.enable_compass:
            try:
                if self._should_run_compass_today():
                    compass_response = self._run_compass(
                        since=since,
                        until=until,
                        is_test_run=False,
                    )
                    response.extend(compass_response)

                    today = datetime.now(timezone.utc).date().isoformat()
                    self._save_compass_last_run_date(today)
                    self.siemplify.LOGGER.info(
                        f"Compass run completed. Saved last_run_date={today}"
                    )
                else:
                    self.siemplify.LOGGER.info(
                        "Skipping Compass because it already ran today."
                    )
            except Exception as e:
                self.siemplify.LOGGER.error(
                    f"Failed to fetch Compass data. Treating as unavailable: {e}"
                )
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
