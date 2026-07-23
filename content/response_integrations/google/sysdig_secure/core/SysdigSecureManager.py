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

import time
from typing import Any

from soar_sdk.SiemplifyConnectors import SiemplifyConnectorExecution
from requests import Session

from TIPCommon.base.utils import NewLineLogger
from TIPCommon.filters import filter_old_alerts

from ..core.SysdigSecureApiUtils import get_full_url, validate_response
from ..core.SysdigSecureConstants import DEFAULT_LIMIT, ONE_HOUR_NS
from ..core.SysdigSecureDatamodels import Event
from ..core.SysdigSecureUtils import build_events_filter
from ..core import SysdigSecureParser as parser


class ApiManager:
    def __init__(
        self,
        api_root: str,
        session: Session,
        logger: NewLineLogger,
    ) -> None:
        """Manager for handling API interactions

        Args:
            session (Session): initialized session object to be used in API session
            logger (NewLineLogger): logger object
        """
        self.api_root = api_root
        self.session = session
        self.logger = logger

    def test_connectivity(self) -> None:
        """Test connectivity."""
        unix_now_ns = time.time_ns()
        params = {
            "from": unix_now_ns - ONE_HOUR_NS,
            "to": unix_now_ns,
            "limit": 1
        }
        response = self.session.get(
            get_full_url(self.api_root, "ping"),
            params=params
        )

        validate_response(response)

    def get_events(
        self,
        start_timestamp: int,
        end_timestamp: int,
        limit: int,
        exclude_rule_names: bool,
        siemplify: SiemplifyConnectorExecution,
        lowest_severity: str = None,
        custom_filter_query: str = None,
        existing_ids: list[str] = None,
        rule_names: list[str] = None,
    ) -> list[Event]:
        """
        Get events

        Args:
            start_timestamp (int): start of timestamp range to fetch events from
            end_timestamp (int): end of timestamp range to fetch events to
            limit (int): limit for results
            exclude_rule_names (bool): specifies if rule names should be excluded or no
            siemplify (SiemplifyConnectorExecution): SiemplifyConnectorExecution object
            lowest_severity (str): lowest severity to use in filter
            custom_filter_query (str): custom filter query to use as filter
            existing_ids (list[str]): list of existing ids to filter
            rule_names (list[str]): rule names to use in filter

        Returns:
            list[Event]: list of event dataclasses
        """
        params = {
            "filter": build_events_filter(
                custom_filter_query,
                lowest_severity,
                rule_names,
                exclude_rule_names
            ),
            "from": start_timestamp,
            "to": end_timestamp,
            "limit": DEFAULT_LIMIT
        }
        url = get_full_url(self.api_root, "get_events")

        return self._paginate_results(url, limit, siemplify, existing_ids, params)

    def _paginate_results(
        self,
        full_url: str,
        limit: int,
        siemplify: SiemplifyConnectorExecution,
        existing_ids: list[str] = None,
        params: dict[str, Any] = None,
    ) -> list[Event]:
        """
        Paginate the results

        Args:
            full_url (str): full url to send request to
            limit (int): limit for the results
            siemplify (SiemplifyConnectorExecution): SiemplifyConnectorExecution object
            existing_ids (list[str]): list of existing ids to filter
            params (dict[str, Any]): request params dict

        Returns:
            list[Event]: list of Event dataclasses
        """
        results, next_page_cursor, response = [], None, None
        params = params or {}

        while True:
            if response:
                if not next_page_cursor:
                    break

                params.pop("from", None)
                params.pop("to", None)
                params["cursor"] = next_page_cursor

            response = self.session.get(full_url, params=params)
            validate_response(response)
            next_page_cursor = response.json().get("page", {}).get("next", "")

            results.extend(
                filter_old_alerts(
                    siemplify,
                    alerts=parser.build_event_objects(response.json()),
                    existing_ids=set(existing_ids) if existing_ids else [],
                    id_key="alert_id",
                )
            )

        sorted_results = sorted(results, key=lambda _alert: _alert.timestamp)
        return sorted_results[:limit] if limit else sorted_results
