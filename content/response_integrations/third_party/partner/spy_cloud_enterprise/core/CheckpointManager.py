from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any


class CheckpointManager:
    def __init__(
        self,
        siemplify: Any,
        checkpoint_name: str = "checkpoint",
        initial_lookback_hours: int = 24,
    ) -> None:
        self.siemplify = siemplify
        self.checkpoint_name = checkpoint_name
        self.initial_lookback_hours = initial_lookback_hours

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
        timestamp = self.load_checkpoint()
        now = datetime.now(timezone.utc)
        until = now.strftime("%Y-%m-%dT%H:%M:%SZ")

        if not timestamp or int(timestamp) <= 0:
            since = (now - timedelta(hours=self.initial_lookback_hours)).strftime("%Y-%m-%dT%H:%M:%SZ")
            return since, until

        last = datetime.fromtimestamp(int(timestamp) / 1000, tz=timezone.utc)
        since = (last + timedelta(seconds=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
        return since, until