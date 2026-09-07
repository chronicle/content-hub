# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Mapping


INTEGRATION_IDENTIFIER: str = "AzureMonitor"
INTEGRATION_DISPLAY_NAME: str = "Azure Monitor"

PING_SCRIPT_NAME: str = f"{INTEGRATION_IDENTIFIER} - Ping"
SEARCH_LOGS_SCRIPT_NAME: str = f"{INTEGRATION_IDENTIFIER} - Search Logs"


DEFAULT_LOGIN_API_ROOT: str = "https://login.microsoftonline.com"
DEFAULT_API_ROOT: str = "https://api.loganalytics.io"
DEFAULT_VERIFY_SSL: bool = True

GRANT_TYPE: str = "client_credentials"
TOKEN_PAYLOAD_FROM_SECRET: Mapping[str, str] = {
    "grant_type": GRANT_TYPE,
    "client_id": "",
    "client_secret": "",
    "resource": "",
}


ENDPOINTS: Mapping[str, str] = {
    "bearer_token_url": "{tenant_id}/oauth2/token",
    "ping": "/v1/workspaces/{workspace_id}/query",
    "search_logs": "/v1/workspaces/{workspace_id}/query",
}

DEFAULT_PING_LOGS_QUERY: str = "AzureActivity"
DEFAULT_MIN_ROWS: int = 1
DEFAULT_TIME_FRAME: str = "Last Hour"
DEFAULT_RESULTS_TO_RETURN: int = 100
MAX_RESULTS_LIMIT: int = 1000


class DDLEnum(Enum):
    @classmethod
    def values(cls) -> list[str]:
        return [item.value for item in cls]


class TimeFrameDDLEnum(DDLEnum):
    LAST_HOUR = "Last Hour"
    LAST_6_HOURS = "Last 6 Hours"
    LAST_24_HOURS = "Last 24 Hours"
    LAST_WEEK = "Last Week"
    LAST_MONTH = "Last Month"
    CUSTOM = "Custom"

    def to_start_time_iso(self) -> datetime.date:
        """
        Converts the selected time frame enum into an ISO 8601 formatted UTC start time
        string.

        This method calculates the start time corresponding to the selected
        `TimeFrameDDLEnum` value (e.g., last hour, last 6 hours, last week, etc.)
        relative to the current UTC time, and returns it as an ISO 8601 string
        with millisecond precision and a 'Z' suffix.

        Raises:
            ValueError: If the enum value is not supported.

        Returns:
            str: The calculated start time in ISO 8601 format with milliseconds and
            UTC indicator. Example: '2025-10-30T08:42:15.123Z'
        """
        now = datetime.now(timezone.utc)
        match self:
            case TimeFrameDDLEnum.LAST_HOUR:
                start_time = now - timedelta(hours=1)
            case TimeFrameDDLEnum.LAST_6_HOURS:
                start_time = now - timedelta(hours=6)
            case TimeFrameDDLEnum.LAST_24_HOURS:
                start_time = now - timedelta(hours=24)
            case TimeFrameDDLEnum.LAST_WEEK:
                start_time = now - timedelta(days=7)
            case TimeFrameDDLEnum.LAST_MONTH:
                start_time = now - timedelta(days=30)
            case _:
                raise ValueError(f"Unsupported timeframe: {self}")

        return start_time.isoformat(timespec="milliseconds").replace("+00:00", "Z")
