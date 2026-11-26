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

from typing import Any
import dataclasses
import requests
from . import MandiantMDParser as parser
from . import api_utils
from TIPCommon.filters import filter_old_alerts
from TIPCommon.types import ChronicleSOAR
from .datamodels import Alert, Event
from . import constants


@dataclasses.dataclass
class ApiParameters:
    api_root: str = None


class ApiManager:
    def __init__(
        self,
        session: requests.Session,
        api_params: ApiParameters,
        chronicle_soar: ChronicleSOAR,
    ) -> None:
        """Manager for handling API interactions

        Args:
            session (requests.Session): session object with corresponding headers
            api_params (ApiParameters): parameters for the API
            chronicle_soar (ChronicleSOAR): ChronicleSOAR object
        """
        self.session = session
        self.api_root = api_params.api_root
        self.siemplify = chronicle_soar
        self.logger = chronicle_soar.LOGGER

    def test_connectivity(self) -> None:
        """Test connectivity"""
        url = api_utils.get_full_url(
            api_root=self.api_root, endpoint_id="test_connectivity"
        )

        response = self.session.get(url)
        api_utils.validate_response(response)

    def get_investigations(
        self,
        timestamp: str,
        end_timestamp: str,
        limit: int,
        alert_statuses: [str] = None,
        existing_ids: [str] = None,
    ) -> list[Alert]:
        """Get alerts

        Args:
            timestamp (str): timestamp filter to get investigations from
            end_timestamp: {str} End timestamp for fetching results until
            limit (int): limit for results
            alert_statuses ([str]): list of alert statuses
            existing_ids ([str]): list of ids to filter

        Returns:
            [Alert]: list of Alert dataclasses
        """
        url = api_utils.get_full_url(
            api_root=self.api_root, endpoint_id="get_investigations"
        )

        params = {
            "filter": api_utils.create_filter_string(
                start_timestamp=timestamp,
                end_timestamp=end_timestamp,
                statuses=alert_statuses,
            )
        }

        results = self._paginate_results(
            full_url=url,
            limit=limit,
            parser_method="build_alert_objects",
            existing_ids=existing_ids,
            params=params,
        )

        return api_utils.filter_alerts_by_source(constants.SOURCE_NAME, results)

    def get_investigation_details(self, external_id: str) -> list[Event]:
        """Get investigation details

        Args:
            external_id (str): external id of the investigation

        Returns:
            [Event]: list of Event dataclasses
        """
        url = api_utils.get_full_url(
            api_root=self.api_root,
            endpoint_id="get_investigation_details",
            external_id=external_id,
        )

        response = self.session.get(url)
        api_utils.validate_response(response)

        return api_utils.filter_events_by_type(
            set(constants.SKIPPED_OBJECTS), parser.build_event_objects(response.json())
        )

    def _paginate_results(
        self,
        full_url: str,
        limit: int,
        parser_method: str,
        id_key: str = "alert_id",
        existing_ids: [str] = None,
        params: dict | None = None,
    ) -> list[Any]:
        """Paginate the results

        Args:
            full_url (str): full url to send request to
            limit (int): limit for the results to fetch
            id_key (str): The key to use for filtering
            existing_ids ([str]): list of ids to filter
            params (dict): request params dict
            parser_method (str): The name of parser method to build the result

        Returns:
            [Any]: list of results
        """
        results, response, page_number = [], None, 0

        while True:
            if response:
                if limit and len(results) >= limit:
                    break

            page_number += 1
            params.update({"page": page_number})
            response = self.session.get(full_url, params=params)
            api_utils.validate_response(response)

            current_items = getattr(parser, parser_method)(response.json())

            results.extend(
                filter_old_alerts(
                    self.siemplify,
                    alerts=current_items,
                    existing_ids=set(existing_ids) if existing_ids else [],
                    id_key=id_key,
                )
            )

            if not current_items:
                break

        return results[:limit] if limit else results
