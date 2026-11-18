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

import dataclasses
import requests

from soar_sdk.SiemplifyConnectors import SiemplifyConnectorExecution
from soar_sdk.SiemplifyLogger import SiemplifyLogger

from TIPCommon.filters import filter_old_alerts
from . import api_utils
from .constants import (
    ALERT_STATUSES,
    ENDPOINTS,
    GTI_ENDPOINTS,
    GTI_ROOT,
    MANDIANT_ROOT,
    MAX_LIMIT,
    SEVERITIES,
)
from .datamodels import Alert
from . import MandiantDTMParser as parser


@dataclasses.dataclass
class ApiParameters:
    api_root: str = None


class ApiManager:
    def __init__(
        self,
        session: requests.Session,
        api_params: ApiParameters,
        logger: SiemplifyLogger,
        gti_api_key: str = None,
    ) -> None:
        """Manager for handling API interactions

        Args:
            session (requests.Session): session object with corresponding headers
            api_params (ApiParameters): parameters for the API
            logger (SiemplifyLogger): logger object
            gti_api_key (str): Google Threat Intelligence API Key
        """
        self.session = session
        self.api_root = api_params.api_root
        self.logger = logger
        self.gti_api_key = gti_api_key

    def set_endpoint(self, endpoint_id: str) -> str:
        """Selects the appropriate endpoint based on the presence of a GTI API key.

        Args:
            endpoint_id (str): The identifier for the desired API endpoint.

        Returns:
            str: API endpoint URL.
        """
        if self.gti_api_key:
            return GTI_ENDPOINTS[endpoint_id]

        return ENDPOINTS[endpoint_id]

    def test_connectivity(self) -> None:
        """Test connectivity"""
        url = api_utils.get_full_url(
            api_root=self.api_root, endpoint=self.set_endpoint("test_connectivity")
        )

        response = self.session.get(url)
        api_utils.validate_response(response)

    def get_alerts(
        self,
        timestamp: str,
        limit: int,
        siemplify: SiemplifyConnectorExecution,
        lowest_severity: str = "",
        monitor_ids: list[str] | None = None,
        alert_types: list[str] | None = None,
        existing_ids: list[str] | None = None,
    ) -> list[Alert]:
        """Get alerts

        Args:
            timestamp (str): timestamp filter to get alert from
            limit (int): limit for results
            siemplify (SiemplifyConnectorExecution): SiemplifyConnectorExecution object
            lowest_severity (str): lowest severity filter
            monitor_ids (list[str] | None ): list of monitor ids filters
            alert_types (list[str] | None ): list of alert type filters
            existing_ids (list[str] | None ): list of ids to filter

        Returns:
            [Alert]: list of Alert dataclasses
        """
        url = api_utils.get_full_url(
            api_root=self.api_root, endpoint=self.set_endpoint("get_alerts")
        )

        params = {
            "since": timestamp,
            "size": max(limit, MAX_LIMIT),
            "severity": (
                SEVERITIES[SEVERITIES.index(lowest_severity.lower()) :]
                if lowest_severity
                else SEVERITIES
            ),
            "monitor_id": monitor_ids,
            "alert_type": alert_types,
            "order": "asc",
            "refs": "true",
            "monitor_name": "true",
            "status": ALERT_STATUSES,
        }

        return self._paginate_results(url, limit, siemplify, existing_ids, params)

    def _paginate_results(
        self,
        full_url: str,
        limit: int,
        siemplify: SiemplifyConnectorExecution,
        existing_ids: [str] = None,
        params: dict | None = None,
    ) -> list[Alert]:
        """Paginate the results

        Args:
            full_url (str): full url to send request to
            limit (int): limit for the results to fetch
            existing_ids ([str]): list of ids to filter
            params (dict): request params dict
            siemplify (SiemplifyConnectorExecution): SiemplifyConnectorExecution object

        Returns:
            [Alert]: list of Alert dataclasses
        """
        results, next_page_link, response = [], None, None

        while True:
            if response:
                if not next_page_link or (limit is not None and len(results) >= limit):
                    break

                full_url = next_page_link
                params = {}

            response = self.session.get(full_url, params=params)

            if self.gti_api_key:
                current_link = response.headers.get("link", "")
                if self.api_root not in current_link:
                    updated_link = current_link.replace(MANDIANT_ROOT, GTI_ROOT)
                    response.headers.update({"link": updated_link})

            api_utils.validate_response(response)
            next_page_link = api_utils.get_next_page_url(response.headers)

            results.extend(
                filter_old_alerts(
                    siemplify,
                    alerts=parser.build_alert_objects(response.json()),
                    existing_ids=set(existing_ids) if existing_ids else [],
                    id_key="alert_id",
                )
            )

        return results[:limit] if limit else results

    def update_alert(self, alert_id: str, status: str):
        """Update alert status

        Args:
            alert_id (str): Alert id
            status (str): Status to update

        Returns:
            response (requests.Response): response object
        """
        url = api_utils.get_full_url(
            api_root=self.api_root,
            endpoint=self.set_endpoint("update_alert"),
            alert_id=alert_id,
        )

        payload = {"status": status}
        response = self.session.patch(url, json=payload)
        api_utils.validate_response(response)
        return response
