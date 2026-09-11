from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

# SpyCloud stamps `spycloud_publish_date` when a record is published, but the
# record only becomes queryable on the publish-date filter some time later. A
# window that ends at `now` therefore returns 0 for records that are published
# but not yet indexed -- and because the checkpoint then advances past them, they
# can never be returned again. Ending every window a fixed distance behind `now`
# gives records time to become queryable before the checkpoint moves past them.
DEFAULT_INGESTION_LAG_MINUTES = 15


class CheckpointManager:
    def __init__(
        self,
        siemplify: Any,
        checkpoint_name: str = "checkpoint",
        initial_lookback_hours: int = 24,
        ingestion_lag_minutes: int = DEFAULT_INGESTION_LAG_MINUTES,
    ) -> None:
        self.siemplify = siemplify
        self.checkpoint_name = checkpoint_name
        self.initial_lookback_hours = initial_lookback_hours
        self.ingestion_lag_minutes = max(0, int(ingestion_lag_minutes))

    def load_checkpoint(self) -> Any:
        return self.siemplify.fetch_timestamp(datetime_format=False, timezone=False)

    def save_checkpoint(self, timestamp_ms: int) -> None:
        self.siemplify.save_timestamp(
            datetime_format=False,
            timezone=False,
            new_timestamp=timestamp_ms
        )

    def iso_to_epoch_ms(self, value: str) -> int:
        dt = datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        return int(dt.timestamp() * 1000)

    def get_next_since_until(self) -> tuple[str, str]:
        """
        Build the next publish-date window.

        `until` trails `now` by ``ingestion_lag_minutes`` so the connector only
        checkpoints past time ranges that SpyCloud has had a chance to fully
        index. The returned window can be empty (``since >= until``) when a cycle
        runs sooner than the lag interval after the previous one; callers must
        treat that as "not yet ready" and leave the checkpoint untouched.
        """
        timestamp = self.load_checkpoint()
        now = datetime.now(timezone.utc)
        until_dt = now - timedelta(minutes=self.ingestion_lag_minutes)
        until = until_dt.strftime("%Y-%m-%dT%H:%M:%SZ")

        if not timestamp or int(timestamp) <= 0:
            since = (now - timedelta(hours=self.initial_lookback_hours)).strftime("%Y-%m-%dT%H:%M:%SZ")
            return since, until

        last = datetime.fromtimestamp(int(timestamp) / 1000, tz=timezone.utc)
        since = (last + timedelta(seconds=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
        return since, until
