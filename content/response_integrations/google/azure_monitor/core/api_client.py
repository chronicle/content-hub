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
from typing import TYPE_CHECKING, NamedTuple

from TIPCommon.base.interfaces import Apiable

from ..core.api_utils import get_full_url, validate_response
from ..core.constants import DEFAULT_MIN_ROWS, DEFAULT_PING_LOGS_QUERY
from ..core.data_parser import parse_azure_monitor_response

if TYPE_CHECKING:
    from requests import Response

    from TIPCommon.base.interfaces.logger import ScriptLogger
    from TIPCommon.types import SingleJson

    from ..core.auth import AuthenticatedSession
    from ..core.data_models import AzureLogEntry


class ApiParameters(NamedTuple):
    api_root: str
    workspace_id: str


class AzureMonitorApiClient(Apiable):
    def __init__(
        self,
        authenticated_session: AuthenticatedSession,
        configuration: ApiParameters,
        logger: ScriptLogger,
    ) -> None:
        super().__init__(
            authenticated_session=authenticated_session,
            configuration=configuration,
        )
        self.logger: ScriptLogger = logger
        self.api_root: str = configuration.api_root
        self.workspace_id: str = configuration.workspace_id

    def test_connectivity(self) -> None:
        """Test connectivity to API."""
        url: str = get_full_url(
            self.api_root,
            endpoint_id="ping",
            workspace_id=self.workspace_id,
        )
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(hours=1)
        time_span = (
            f"{start_time.isoformat(timespec='milliseconds')}/"
            f"{end_time.isoformat(timespec='milliseconds')}"
        )
        payload: dict[str, str] = {
            "query": DEFAULT_PING_LOGS_QUERY,
            "maxRows": DEFAULT_MIN_ROWS,
            "timespan": time_span,
        }

        response: Response = self.session.post(
            url,
            json=payload,
        )
        validate_response(response)

    def search_logs(
        self,
        query: str,
        start_time: str,
        end_time: str,
        max_rows: int,
        workspace_id: str | None = None,
    ) -> list[AzureLogEntry]:
        """Search logs in Azure Monitor.
        Args:
            query (str): The query to execute.
            start_time (str): The start time for the query in ISO 8601 format.
            end_time (str): The end time for the query in ISO 8601 format.
            max_rows (int): The maximum number of rows to return.
            workspace_id (str | None): The workspace ID to use. If None, uses the
            default.

        Returns:
            list[AzureLogEntry]: The list of AzureLogEntry objects.
        """
        workspace_id: str = workspace_id or self.workspace_id

        url: str = get_full_url(
            self.api_root,
            endpoint_id="search_logs",
            workspace_id=workspace_id,
        )
        time_span: str = f"{start_time}/{end_time}"
        payload: dict[str, str | int] = {
            "query": query,
            "maxRows": max_rows,
            "timespan": time_span,
        }

        response: Response = self.session.post(url, json=payload)
        validate_response(response)

        return parse_azure_monitor_response(response.json())
