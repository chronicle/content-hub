from __future__ import annotations

import datetime
from typing import Any

# Fixed clock so tests never depend on wall time.
NOW_MS: int = 1786000000000
HOUR_MS: int = 60 * 60 * 1000


def to_iso(timestamp_ms: int) -> str:
    """Render a timestamp the way the API renders datetimes: ISO 8601 with offset."""
    return datetime.datetime.fromtimestamp(
        timestamp_ms / 1000, tz=datetime.timezone.utc
    ).isoformat()


def build_alert_row(
    alert_id: str,
    created_at_ms: int,
    last_sync_ms: int,
    severity: str = "critical",
    orca_score: float = 9.0,
) -> dict[str, Any]:
    """A single alert as the serving layer query endpoint returns it.

    Field values are wrapped in a {"value": ...} object and datetimes are
    timezone-aware ISO 8601 strings. This mirrors a response captured from the
    live API - the connector's cursor logic depends on both properties, so these
    fixtures pin them.
    """
    return {
        "data": {
            "AlertId": {"value": alert_id},
            "Title": {"value": f"Alert {alert_id}"},
            "Details": {"value": "Alert details"},
            "Severity": {"value": severity},
            "CreatedAt": {"value": to_iso(created_at_ms)},
            "last_sync": {"value": to_iso(last_sync_ms)},
            "OrcaScore": {"value": orca_score},
            "AlertType": {"value": "test_alert_type"},
            "Category": {"value": "Test Category"},
            "Type": {"value": "test_type"},
            "AssetData": {
                "value": {"asset_name": f"asset-for-{alert_id}", "asset_type": "vm"}
            },
        }
    }


def build_response(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Wrap alert rows in the endpoint's envelope."""
    return {"data": rows}


class FakeLogger:
    def __init__(self) -> None:
        self.messages: list[str] = []

    def info(self, message: str) -> None:
        self.messages.append(f"INFO: {message}")

    def warn(self, message: str) -> None:
        self.messages.append(f"WARN: {message}")

    def error(self, message: str) -> None:
        self.messages.append(f"ERROR: {message}")

    def exception(self, error: Exception) -> None:
        self.messages.append(f"EXCEPTION: {error!r}")


class FakeSiemplify:
    """Stands in for SiemplifyConnectorExecution.

    Keeps the saved timestamp in an external ``state`` dict so consecutive
    connector iterations can share it, the way the platform database does.
    """

    def __init__(self, parameters: dict[str, Any], state: dict[str, Any]) -> None:
        self.script_name = ""
        self.parameters = parameters
        self.LOGGER = FakeLogger()
        self.whitelist: list[str] = []
        self.context = type("Ctx", (), {"connector_info": None})()
        self._state = state
        self.returned_alerts: list[Any] = []

    def fetch_timestamp(self, datetime_format: bool = False, timezone: bool = False):
        timestamp = self._state.get("timestamp", 0)
        if datetime_format:
            return datetime.datetime.fromtimestamp(
                timestamp / 1000, tz=datetime.timezone.utc
            )
        return timestamp

    def save_timestamp(self, new_timestamp: int, **kwargs: Any) -> None:
        self._state["timestamp"] = new_timestamp

    def return_package(self, alerts: list[Any], *args: Any, **kwargs: Any) -> None:
        self.returned_alerts = alerts


class FakeManager:
    """Serves canned alert rows using the endpoint's filter/order/paging semantics.

    ``last_sync`` and ``CreatedAt`` ranges are inclusive on both ends, results are
    ordered by ``last_sync`` ascending, and ``start_at_index`` offsets into them -
    all verified against the live API.
    """

    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self.rows = rows
        self.calls: list[dict[str, Any]] = []

    def get_alerts(
        self,
        start_timestamp: int,
        limit: int,
        last_sync_start_timestamp: int | None = None,
        start_at_index: int = 0,
        lowest_score: float | None = None,
        **kwargs: Any,
    ) -> list[Any]:
        from ..core.OrcaSecurityParser import OrcaSecurityParser

        self.calls.append(
            {
                "start_timestamp": start_timestamp,
                "limit": limit,
                "last_sync_start_timestamp": last_sync_start_timestamp,
                "start_at_index": start_at_index,
            }
        )

        def created_at(row: dict[str, Any]) -> int:
            return _iso_to_ms(row["data"]["CreatedAt"]["value"])

        def last_sync(row: dict[str, Any]) -> int:
            return _iso_to_ms(row["data"]["last_sync"]["value"])

        matching = [row for row in self.rows if created_at(row) >= start_timestamp]
        if last_sync_start_timestamp is not None:
            matching = [
                row for row in matching if last_sync(row) >= last_sync_start_timestamp
            ]
        if lowest_score is not None:
            matching = [
                row
                for row in matching
                if row["data"]["OrcaScore"]["value"] >= lowest_score
            ]

        matching.sort(key=last_sync)
        page = matching[start_at_index : start_at_index + limit]
        return OrcaSecurityParser().build_alert_objects(build_response(page))


def _iso_to_ms(value: str) -> int:
    return int(datetime.datetime.fromisoformat(value).timestamp() * 1000)


DEFAULT_PARAMETERS: dict[str, Any] = {
    "API Root": "https://api.example.test",
    "API Key": "",
    "API Token": "token",
    "Verify SSL": "false",
    "Environment Field Name": "",
    "Environment Regex Pattern": ".*",
    "PythonProcessTimeout": "180",
    "Category Filter": "",
    "Alert Type Filter": "",
    "Lowest Severity To Fetch": "",
    "Max Hours Backwards": "3",
    "Max Alerts To Fetch": "100",
    "Use dynamic list as a blacklist": "false",
    "DeviceProductField": "Product Name",
    "Lowest Orca Score To Fetch": "",
}
